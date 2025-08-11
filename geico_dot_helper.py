#!/usr/bin/env python3
"""Helper script specifically for GEICO DOT number entry"""

def get_geico_dot_entry_script(dot_number="111111111"):
    """Generate JavaScript specifically for GEICO's DOT field"""
    return f"""
    (function() {{
        console.log('GEICO DOT Entry Helper - Starting...');
        
        // Method 1: Try to find by analyzing all inputs
        const allInputs = Array.from(document.querySelectorAll('input'));
        console.log('Total inputs found:', allInputs.length);
        
        // Log all visible inputs for debugging
        const visibleInputs = allInputs.filter(input => {{
            const rect = input.getBoundingClientRect();
            return input.offsetParent !== null && rect.width > 0 && rect.height > 0;
        }});
        
        console.log('Visible inputs:', visibleInputs.length);
        visibleInputs.forEach((input, idx) => {{
            console.log(`Input #${{idx}}: type=${{input.type}}, name=${{input.name}}, id=${{input.id}}, placeholder=${{input.placeholder}}, value='${{input.value}}'`);
        }});
        
        // GEICO-specific: The DOT field is usually the second visible text input after ZIP
        let dotField = null;
        
        // First, try to find explicitly by DOT-related attributes
        for (let input of visibleInputs) {{
            const attrs = (input.name + input.id + input.placeholder + (input.getAttribute('aria-label') || '')).toLowerCase();
            if (attrs.includes('dot') || attrs.includes('usdot') || attrs.includes('us dot')) {{
                dotField = input;
                console.log('Found DOT field by attribute match');
                break;
            }}
        }}
        
        // If not found, use position-based approach (second text field)
        if (!dotField) {{
            const textInputs = visibleInputs.filter(input => 
                input.type === 'text' || input.type === 'number' || !input.type
            );
            
            if (textInputs.length >= 2) {{
                // Skip ZIP field (usually first) and get the next one
                dotField = textInputs[1];
                console.log('Using second text input as DOT field');
            }}
        }}
        
        // If still not found, look for any empty text field that's not ZIP
        if (!dotField) {{
            dotField = visibleInputs.find(input => {{
                const isTextField = input.type === 'text' || input.type === 'number' || !input.type;
                const attrs = (input.name + input.id + input.placeholder).toLowerCase();
                const isEmpty = input.value === '';
                const notZip = !attrs.includes('zip') && !attrs.includes('postal');
                return isTextField && isEmpty && notZip;
            }});
            
            if (dotField) {{
                console.log('Found empty non-ZIP field for DOT');
            }}
        }}
        
        if (dotField) {{
            console.log('DOT field found! Attempting to enter value...');
            
            // Visual feedback
            dotField.style.border = '3px solid green';
            dotField.style.backgroundColor = '#e6ffe6';
            
            // Ensure field is in view
            dotField.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            
            // Focus the field
            dotField.focus();
            dotField.click();
            
            // Method 1: Direct value assignment with all events
            dotField.value = '';  // Clear first
            
            // Set the value character by character
            const dotNumber = '{dot_number}';
            for (let i = 0; i < dotNumber.length; i++) {{
                dotField.value += dotNumber[i];
                
                // Fire input event for each character
                dotField.dispatchEvent(new InputEvent('input', {{
                    data: dotNumber[i],
                    inputType: 'insertText',
                    bubbles: true
                }}));
            }}
            
            // Fire all possible events that GEICO might be listening to
            const events = ['input', 'change', 'keyup', 'blur', 'focusout'];
            events.forEach(eventType => {{
                dotField.dispatchEvent(new Event(eventType, {{ bubbles: true }}));
            }});
            
            // Verify the value was set
            console.log('DOT field value after entry:', dotField.value);
            
            // Remove visual feedback after a moment
            setTimeout(() => {{
                dotField.style.border = '';
                dotField.style.backgroundColor = '';
            }}, 2000);
            
            return {{
                success: true,
                value: dotField.value,
                fieldInfo: {{
                    type: dotField.type,
                    name: dotField.name,
                    id: dotField.id,
                    placeholder: dotField.placeholder
                }}
            }};
        }} else {{
            console.error('Could not find DOT field!');
            
            // Return debug info
            return {{
                success: false,
                error: 'DOT field not found',
                visibleInputCount: visibleInputs.length,
                inputs: visibleInputs.map(input => ({{
                    type: input.type,
                    name: input.name,
                    id: input.id,
                    placeholder: input.placeholder,
                    value: input.value ? '[has value]' : '[empty]'
                }}))
            }};
        }}
    }})();
    """

def get_force_type_script(dot_number="111111111"):
    """Alternative script that forces typing using execCommand"""
    return f"""
    (function() {{
        // Find the second visible text input (assumed to be DOT field)
        const textInputs = Array.from(document.querySelectorAll('input'))
            .filter(input => {{
                const rect = input.getBoundingClientRect();
                return input.offsetParent !== null && 
                       rect.width > 0 && 
                       rect.height > 0 &&
                       (input.type === 'text' || input.type === 'number' || !input.type);
            }});
        
        if (textInputs.length >= 2) {{
            const dotField = textInputs[1];
            
            // Focus and select all
            dotField.focus();
            dotField.select();
            
            // Use execCommand to type (older but sometimes more compatible)
            document.execCommand('delete');
            document.execCommand('insertText', false, '{dot_number}');
            
            return {{
                success: true,
                value: dotField.value
            }};
        }}
        
        return {{ success: false, error: 'Not enough text inputs found' }};
    }})();
    """

if __name__ == "__main__":
    print("GEICO DOT Helper loaded")
    print("Use get_geico_dot_entry_script() to get the JavaScript for DOT entry")