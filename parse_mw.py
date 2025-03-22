import re
import json
from pathlib import Path

def parse_dictionary(input_file):
    print("Starting to parse dictionary...")
    dictionary = []
    current_word = ""
    current_meaning = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Look for new entry
            if line.startswith('<L>'):
                # Save previous entry if exists
                if current_word:
                    dictionary.append({
                        "word": current_word,
                        "meaning": ' '.join(current_meaning).strip()
                    })
                    
                # Get new word
                word_match = re.search(r'<k1>([^<]+)', line)
                current_word = word_match.group(1) if word_match else ""
                current_meaning = []
                
            # Add to meaning if it's a content line
            elif not line.startswith('[Page') and not line.startswith('<L') and line.strip():
                # Clean up the line
                cleaned = re.sub(r'\{[^}]+\}', '', line)  # Remove markup
                cleaned = re.sub(r'<[^>]+>', '', cleaned)  # Remove XML tags
                cleaned = re.sub(r'¦', '', cleaned)        # Remove broken bar
                cleaned = cleaned.strip()
                if cleaned:
                    current_meaning.append(cleaned)
    
    # Don't forget the last entry
    if current_word:
        dictionary.append({
            "word": current_word,
            "meaning": ' '.join(current_meaning).strip()
        })
    
    print(f"Finished parsing. Found {len(dictionary)} entries.")
    return dictionary

def main():
    # Get the current directory
    current_dir = Path.cwd()
    
    # Define input and output files
    input_file = current_dir / 'mw72.txt'
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