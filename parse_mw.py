import re
import json
from pathlib import Path

def slp1_to_iast_map():
    return {
        'a': 'a', 'A': 'ā', 'i': 'i', 'I': 'ī', 'u': 'u', 'U': 'ū',
        'f': 'ṛ', 'F': 'ṝ', 'x': 'ḷ', 'X': 'ḹ', 'e': 'e', 'E': 'ai',
        'o': 'o', 'O': 'au', 'M': 'ṃ', 'H': 'ḥ', '~': 'ṁ',
        'k': 'k', 'K': 'kh', 'g': 'g', 'G': 'gh', 'N': 'ṅ',
        'c': 'c', 'C': 'ch', 'j': 'j', 'J': 'jh', 'Y': 'ñ',
        'w': 'ṭ', 'W': 'ṭh', 'q': 'ḍ', 'Q': 'ḍh', 'R': 'ṇ',
        't': 't', 'T': 'th', 'd': 'd', 'D': 'dh', 'n': 'n',
        'p': 'p', 'P': 'ph', 'b': 'b', 'B': 'bh', 'm': 'm',
        'y': 'y', 'r': 'r', 'l': 'l', 'v': 'v',
        'S': 'ś', 'z': 'ṣ', 's': 's', 'h': 'h',
    }

def slp1_to_iast(text):
    if not text:
        return text
    
    conversion_map = slp1_to_iast_map()
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        if char in conversion_map:
            result.append(conversion_map[char])
        else:
            result.append(char)
        i += 1
    return ''.join(result)

def extract_root(text, term):
    root_patterns = [
        # Match "cl. N. P." pattern first
        r'cl\.\s*(\d+)\s*\.\s*(?:P\.|A\.|Ā\.)\s+([^\s,;()]+)',
        # Match root with class number
        r'(?:√|rt\.|root)\s*([^\s,;()]+)(?:\s*(?:cl\.|class)\s*(\d+))?',
        # Match parenthetical root
        r'\((?:√|rt\.|root)\s*([^\s,;()]+)\)'
    ]
    
    # Words that should not be considered roots
    invalid_words = {'to', 'the', 'a', 'an', 'or', 'and', 'see', 'cf', 'also', 'according', 'was', 'probably'}
    
    for pattern in root_patterns:
        root_match = re.search(pattern, text, re.IGNORECASE)
        if root_match:
            if pattern.startswith(r'cl\.'):
                # For "cl. N. P. root" pattern
                root = root_match.group(2)
                class_num = root_match.group(1)
            else:
                # For other patterns
                root = root_match.group(1)
                class_num = root_match.group(2) if root_match.lastindex > 1 else ""
            
            # Clean up the root
            root = root.strip('.,;()[]{}')
            
            # Skip if root is invalid
            if (root.lower() in invalid_words or 
                len(root) < 2 or
                re.search(r'[.;,()=]', root)):
                continue
                
            return f"{root} {class_num}".strip()
    
    # If no root found but it's a verb entry with class number, use the term itself
    if re.search(r'cl\.\s*(\d+)', text):
        class_match = re.search(r'cl\.\s*(\d+)', text)
        return f"{term} {class_match.group(1)}"
    
    return ""

def clean_definition(text):
    """Clean up definition text to make it more parseable"""
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Fix broken parentheses
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    # Fix broken dots
    text = re.sub(r'\s+\.\s+', '. ', text)
    # Fix broken colons
    text = re.sub(r'\s+:\s+', ': ', text)
    # Remove q. v. references
    text = re.sub(r'q\.\s*v\.', '', text)
    # Clean up multiple spaces after punctuation
    text = re.sub(r'([.,;:])\s+', r'\1 ', text)
    return text

def extract_verb_forms(text):
    """Extract present tense forms mentioned in the definition"""
    # Clean the text first
    text = clean_definition(text)
    
    forms = []
    patterns = [
        # Match after class number with optional A. form
        r'cl\.\s*\d+\.\s*P\.\s*\([^)]*?also\s*A\.\)',  # Find the class pattern first
        r'cl\.\s*\d+\.\s*P\.\s*(\w+ati)',              # Match P. form
        r'cl\.\s*\d+\.\s*A\.\s*(\w+ate)',              # Match A. form
        # Match parenthetical forms
        r'\([^)]*?also\s*(?:A\.|P\.|Ā\.)\s*(\w+(?:ati|ate))\)',
        # Match other verb forms
        r'(?<=\s)(?:P\.|A\.|Ā\.)\s+(\w+(?:ati|ate))\b'
    ]
    
    # Debug the text
    print(f"\nCleaned definition: {text[:200]}")
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Get all capturing groups
                for i in range(1, match.lastindex + 1 if match.lastindex else 2):
                    form = match.group(i)
                    if form and len(form) > 2:
                        # Verify it's a Sanskrit verb form
                        if re.search(r'(?:ati|ate)$', form):
                            forms.append(form)
                            print(f"Found form {form} with pattern {pattern}")
            except (IndexError, AttributeError):
                continue
    
    # If we found no forms but it's clearly a verb (has cl. N), try harder
    if not forms and re.search(r'cl\.\s*\d+\.', text):
        # Look for any word ending in ati/ate near class number
        near_class = re.search(r'cl\.\s*\d+\.[^.]+?(\w+(?:ati|ate))', text)
        if near_class:
            form = near_class.group(1)
            if form and len(form) > 2:
                forms.append(form)
                print(f"Found fallback form: {form}")
    
    return list(set(forms))

def parse_dictionary(input_file):
    print("Starting to parse dictionary...")
    dictionary = []
    current_term = ""
    current_definition = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('<L>'):
                if current_term:
                    definition_text = ' '.join(current_definition).strip()
                    definition_text = clean_definition(definition_text)
                    
                    entry = {
                        "term": current_term,
                        "definition": definition_text,
                        "part_of_speech": extract_part_of_speech(definition_text),
                        "gender": extract_gender(definition_text)
                    }
                    
                    dictionary.append(entry)
                    
                word_match = re.search(r'<k1>([^<]+)', line)
                current_term = slp1_to_iast(word_match.group(1)) if word_match else ""
                current_definition = []
                
            elif not line.startswith('[Page') and not line.startswith('<L') and line.strip():
                cleaned = re.sub(r'\{[^}]+\}', '', line)
                cleaned = re.sub(r'<[^>]+>', '', cleaned)
                cleaned = re.sub(r'¦', '', cleaned)
                cleaned = cleaned.strip()
                if cleaned:
                    current_definition.append(cleaned)
    
    # Don't forget the last entry
    if current_term:
        definition_text = ' '.join(current_definition).strip()
        definition_text = clean_definition(definition_text)
        
        dictionary.append({
            "term": current_term,
            "definition": definition_text,
            "part_of_speech": extract_part_of_speech(definition_text),
            "gender": extract_gender(definition_text)
        })

    print(f"Finished parsing. Found {len(dictionary)} entries.")
    return dictionary

def extract_part_of_speech(text):
    # More specific verb patterns
    verb_patterns = [
        r'\bcl\.\s*\d+\s*\.\s*(?:P\.|A\.|Ā\.|[PĀA]\.)',  # Class pattern
        r'√\s*[^\s,;]+(?:\s*(?:cl\.|class)\s*\d+)?',     # Root pattern
        r'\(√[^\s,;]+\)',                                 # Parenthetical root
        r'\bDenom\.\s*(?:P\.|A\.|Ā\.|[PĀA]\.)',          # Denominative
        r'\bCaus\.',                                      # Causative
        r'\bIntens\.',                                    # Intensive
        r'\bDesid\.'                                      # Desiderative
    ]
    
    # Check for verb patterns
    for pattern in verb_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 'verb'
    
    # Check for noun pattern
    if re.search(r'\b(?:m\.|f\.|n\.|mfn\.|subst\.)', text, re.IGNORECASE):
        return 'noun'
    
    return ""

def extract_gender(text):
    # Check for compound gender first (case insensitive)
    if re.search(r'\b(?:mfn|m\.f\.n)\.\b', text, re.IGNORECASE):
        return "masculine/feminine/neuter"
    
    # Basic gender patterns with word boundaries and optional spaces
    genders = []
    if re.search(r'\bm\.?\b', text, re.IGNORECASE):  # Match 'm.' or 'm'
        genders.append('masculine')
    if re.search(r'\bf\.?\b', text, re.IGNORECASE):  # Match 'f.' or 'f'
        genders.append('feminine')
    if re.search(r'\bn\.?\b', text, re.IGNORECASE):  # Match 'n.' or 'n'
        genders.append('neuter')
    
    # Join multiple genders with forward slash
    return "/".join(genders) if genders else ""

def main():
    # Get the current directory
    current_dir = Path.cwd()
    
    # Define input and output files
    input_file = current_dir / 'monier-williams' / 'txt' / 'mw72.txt'
    output_file = current_dir / 'sanskrit_dictionary.json'
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Cannot find input file at {input_file}")
        return
    
    try:
        # Parse the dictionary
        dictionary = parse_dictionary(str(input_file))
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
        
        print(f"Dictionary saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()