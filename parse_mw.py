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
    
    # Define all conjugation fields
    conjugation_fields = [
        # Present (lat)
        'lat_1s', 'lat_2s', 'lat_3s',  # singular
        'lat_1d', 'lat_2d', 'lat_3d',  # dual
        'lat_1p', 'lat_2p', 'lat_3p',  # plural
        # Past (lan)
        'lan_1s', 'lan_2s', 'lan_3s',  # singular
        'lan_1d', 'lan_2d', 'lan_3d',  # dual
        'lan_1p', 'lan_2p', 'lan_3p',  # plural
        # Future (lrt)
        'lrt_1s', 'lrt_2s', 'lrt_3s',  # singular
        'lrt_1d', 'lrt_2d', 'lrt_3d',  # dual
        'lrt_1p', 'lrt_2p', 'lrt_3p',  # plural
        # Perfect (lit)
        'lit_1s', 'lit_2s', 'lit_3s',  # singular
        'lit_1d', 'lit_2d', 'lit_3d',  # dual
        'lit_1p', 'lit_2p', 'lit_3p'   # plural
    ]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('<L>'):
                if current_term:
                    definition_text = ' '.join(current_definition).strip()
                    definition_text = clean_definition(definition_text)
                    pos = extract_part_of_speech(definition_text)
                    
                    # Create base entry
                    entry = {
                        "term": current_term,
                        "definition": definition_text,
                        "part_of_speech": pos,
                        "gender": extract_gender(definition_text)
                    }
                    
                    # Add conjugation fields (empty by default)
                    for field in conjugation_fields:
                        entry[field] = ""
                    
                    # If it's a verb, try to extract conjugations
                    if pos == 'verb':
                        conjugations = extract_conjugations(definition_text)
                        entry.update(conjugations)
                    
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

def extract_conjugations(text):
    """Extract all conjugation forms from the definition"""
    conjugations = {
        # Initialize all conjugation fields to empty strings
        'lat_1s': "", 'lat_2s': "", 'lat_3s': "",
        'lat_1d': "", 'lat_2d': "", 'lat_3d': "",
        'lat_1p': "", 'lat_2p': "", 'lat_3p': "",
        'lan_1s': "", 'lan_2s': "", 'lan_3s': "",
        'lan_1d': "", 'lan_2d': "", 'lan_3d': "",
        'lan_1p': "", 'lan_2p': "", 'lan_3p': "",
        'lrt_1s': "", 'lrt_2s': "", 'lrt_3s': "",
        'lrt_1d': "", 'lrt_2d': "", 'lrt_3d': "",
        'lrt_1p': "", 'lrt_2p': "", 'lrt_3p': "",
        'lit_1s': "", 'lit_2s': "", 'lit_3s': "",
        'lit_1d': "", 'lit_2d': "", 'lit_3d': "",
        'lit_1p': "", 'lit_2p': "", 'lit_3p': ""
    }
    
    # Clean and standardize text
    text = clean_definition(text)
    
    # Patterns for each tense section
    tense_sections = {
        'lat': [
            r'Pres\.\s*(?:Indic\.)?\s*([^;.]+)',
            r'(?:cl\.\s*\d+\.\s*)?(?:P\.|A\.|Ā\.)\s+([^;.]+)',
        ],
        'lan': [
            r'(?:Imperf\.|laṅ)\s*([^;.]+)',
            r'(?<=\s)a-[^;.]+',  # Imperfect often starts with 'a-'
        ],
        'lrt': [
            r'(?:Fut\.|lṛṭ)\s*([^;.]+)',
            r'\b\w+iṣyati\b[^;.]*',  # Future forms often end in iṣyati
        ],
        'lit': [
            r'(?:Perf\.|liṭ)\s*([^;.]+)',
            r'(?<=\s)(?:[\w-]+āṃ\s+(?:cakāra|āsa|babhūva))[^;.]*'  # Perfect forms
        ]
    }
    
    # Extract each tense section
    for tense, patterns in tense_sections.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tense_text = match.group(1) if match.groups() else match.group(0)
                forms = extract_forms_from_tense(tense_text, tense)
                conjugations.update(forms)
                break  # Stop after first match for this tense
    
    return conjugations

def extract_forms_from_tense(text, tense):
    """Extract individual conjugation forms from a tense block"""
    forms = {}
    
    # Endings and pronouns for each person-number combination
    person_markers = {
        # Format: (ending pattern, optional pronoun)
        '1s': (r'(?:āmi|ami)\b', r'aham'),
        '2s': (r'(?:asi|si)\b', r'tvam'),
        '3s': (r'(?:ati|ti)\b', r'saḥ'),
        '1d': (r'(?:āvaḥ|vaḥ)\b', r'āvām'),
        '2d': (r'(?:athaḥ|thaḥ)\b', r'yuvām'),
        '3d': (r'(?:ataḥ|taḥ)\b', r'tau'),
        '1p': (r'(?:āmaḥ|maḥ)\b', r'vayam'),
        '2p': (r'(?:atha|tha)\b', r'yūyam'),
        '3p': (r'(?:anti|ati)\b', r'te')
    }
    
    # Special patterns for different tenses
    tense_specific = {
        'lan': {
            'prefix': r'a',  # Imperfect prefix
            'modifications': {'ati': 'at', 'anti': 'an'}  # Ending modifications
        },
        'lrt': {
            'infix': r'iṣy',  # Future infix
            'modifications': {}
        },
        'lit': {
            'reduplications': True,  # Perfect uses reduplication
            'modifications': {'ati': 'a', 'anti': 'uḥ'}
        }
    }
    
    # Look for each person-number combination
    for person, (ending, pronoun) in person_markers.items():
        form_key = f"{tense}_{person}"
        
        # Build pattern based on tense
        if tense in tense_specific:
            spec = tense_specific[tense]
            if 'prefix' in spec:
                pattern = fr'\b{spec["prefix"]}(\w+{ending})\b'
            elif 'infix' in spec:
                pattern = fr'\b(\w+{spec["infix"]}{ending})\b'
            else:
                pattern = fr'\b(\w+{ending})\b'
        else:
            pattern = fr'\b(\w+{ending})\b'
        
        # Try to find the form
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            forms[form_key] = match.group(1)
        else:
            # Try alternative pattern with pronoun if available
            alt_pattern = fr'{pronoun}\s+(\w+)\b'
            match = re.search(alt_pattern, text, re.IGNORECASE)
            if match:
                forms[form_key] = match.group(1)
            else:
                forms[form_key] = ""
    
    return forms

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