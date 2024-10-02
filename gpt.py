import openai
import subprocess
import sys
import importlib
import re
import time

# Set your OpenAI API key here
openai.api_key = ''
RETRY_LIMIT = 5  # Limit the number of retries

def install_module(module_name):
    """
    Install the given Python module using pip if it's not already installed.
    """
    try:
        # Try to import the module to check if it's installed
        __import__(module_name)
    except ImportError:
        # If the module is not installed, install it via pip
        if module_name == 'nmap':
            module_name = 'python-nmap'  # Correct the module name to 'python-nmap'
        print(f"Module '{module_name}' is missing. Installing it...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])

        # Reload the module after installing it
        globals()[module_name] = importlib.import_module(module_name)

def ask_chatgpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Use "gpt-4" or "gpt-3.5-turbo" based on your needs
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,  # Adjust this value for the length of the response
        n=1,  # Number of responses to generate
        temperature=0.7,  # Adjust for more/less randomness in responses
    )

    # Extract the assistant's message
    message = response['choices'][0]['message']['content'].strip()
    return message

def check_for_incomplete_code(code):
    """
    Check for incomplete code, including unterminated strings or unbalanced braces.
    """
    # Check if parentheses, brackets, or braces are balanced
    if code.count('(') != code.count(')') or code.count('[') != code.count(']') or code.count('{') != code.count('}'):
        return False
    # Check for unterminated strings (uneven number of single/double quotes)
    if code.count("'") % 2 != 0 or code.count('"') % 2 != 0:
        return False
    return True

def fix_incomplete_code(code):
    """
    Auto-fix common issues like unterminated print statements or missing indents.
    """
    # Attempt to fix incomplete print statements (detects common patterns)
    if "print(f" in code and not code.strip().endswith(")"):
        code += ')  # Auto-fixing incomplete print statement'
    
    # Fix if __name__ == "__main__": block if it's incomplete
    if "__name__" in code and "__main__" in code and code.strip().endswith(":"):
        code += '\n    print("Executing main block")'  # Add a basic print statement as a placeholder
    
    return code

def add_function_call(code):
    """
    Detects and calls any defined function if it hasn't been called.
    """
    # Find the defined function using a regex search
    function_match = re.search(r'def (\w+)\(.*\):', code)
    if function_match:
        function_name = function_match.group(1)
        # If the function is defined but not called, append the function call at the end
        if function_name not in code:
            code += f'\n\n{function_name}("")  # Automatically calling the function with an IP'
    return code

def execute_python_code(code):
    try:
        # Install modules if they are mentioned in the code
        if "import" in code:
            for line in code.splitlines():
                if line.startswith("import"):
                    module_name = line.split(" ")[1]
                    install_module(module_name)

        # Check if code is incomplete
        if not check_for_incomplete_code(code):
            print("The code contains unterminated strings or braces. Retrying the same prompt automatically...")
            return False

        # Fix incomplete code if possible
        code = fix_incomplete_code(code)

        # Add function call if a function is defined but not called
        code = add_function_call(code)

        # Execute the code safely
        exec(code)
        return True
    except Exception as e:
        print(f"Error executing code: {e}")
        return False

if __name__ == "__main__":
    print("You can now interact with ChatGPT. Type 'exit' to quit.")
    while True:
        user_input = input("\nEnter your prompt: ")
        if user_input.lower() == 'exit':
            print("Exiting ChatGPT interaction. Goodbye!")
            break
        
        retry_count = 0
        while retry_count < RETRY_LIMIT:
            response = ask_chatgpt(user_input)
            print("\nChatGPT Response:\n", response)

            # Check if the response contains Python code and attempt to execute it
            if '```python' in response and '```' in response:
                code = response.split('```python')[1].split('```')[0]
                print("\nExtracted Python Code:\n", code)

                print("\nExecuting Python code...\n")
                success = execute_python_code(code)

                if success:
                    break  # Exit retry loop if execution was successful
            else:
                print("No Python code to execute.")
                break
            retry_count += 1
            if retry_count < RETRY_LIMIT:
                print(f"\nRetrying the same prompt in 3 seconds... (Attempt {retry_count}/{RETRY_LIMIT})")
                time.sleep(3)  # Wait before retrying
            else:
                print(f"Exceeded retry limit of {RETRY_LIMIT}. Unable to get a complete code response.")
                break
