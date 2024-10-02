import openai
import subprocess
import sys
import importlib
import re
import time
import os

# Set your OpenAI API key here
openai.api_key = ''
RETRY_LIMIT = 100  # Limit the number of retries
GENERATED_CODE_FOLDER = "generated_code"  # Directory to save generated code

def install_module(module_name):
    """
    Install the given Python module using pip if it's not already installed.
    """
    try:
        __import__(module_name)
    except ImportError:
        print(f"Module '{module_name}' is missing. Installing it...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])

def ask_chatgpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        n=1,
        temperature=0.7,
    )

    message = response['choices'][0]['message']['content'].strip()
    return message

def suggest_alternative_prompt(rejected_prompt):
    """
    Ask ChatGPT to suggest a new, ethical prompt based on the rejected one.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"The following prompt was ethically rejected: {rejected_prompt}. Can you suggest a new prompt that follows ethical guidelines?"}
        ],
        max_tokens=100,
        n=1,
        temperature=0.7,
    )
    
    new_prompt = response['choices'][0]['message']['content'].strip()
    return new_prompt

def handle_ethics_rejection(response, rejected_prompt):
    """
    Detects if the response includes an ethical rejection and suggests a new prompt.
    """
    if "Sorry" in response and "assist" in response:
        print("ChatGPT has ethically refused this request.")
        new_prompt = suggest_alternative_prompt(rejected_prompt)
        print(f"Suggested prompt: {new_prompt}")
        return new_prompt
    return None

def check_for_incomplete_code(code):
    if code.count('(') != code.count(')') or code.count('[') != code.count(']') or code.count('{') != code.count('}'):
        return False
    if code.count("'") % 2 != 0 or code.count('"') % 2 != 0:
        return False
    return True

def fix_incomplete_code(code):
    if "print(f" in code and not code.strip().endswith(")"):
        code += ')'
    if "__name__" in code and "__main__" in code and code.strip().endswith(":"):
        code += '\n    main()'
    
    return code

def add_function_call(code):
    if "__name__" in code and "__main__" in code:
        return code

    function_match = re.search(r'def (\w+)\(.*\):', code)
    if function_match:
        function_name = function_match.group(1)
        code += f'\n\n{function_name}()'
    return code

def install_from_chatgpt_response(response):
    """
    This function looks for pip install commands in the ChatGPT response and installs the required libraries.
    """
    install_commands = re.findall(r'pip install (\w+)', response)
    for module in install_commands:
        install_module(module)

def save_generated_code(code):
    """
    Save the generated code to a file in the generated_code folder.
    """
    # Ensure the folder exists
    if not os.path.exists(GENERATED_CODE_FOLDER):
        os.makedirs(GENERATED_CODE_FOLDER)
        print(f"Directory '{GENERATED_CODE_FOLDER}' created.")
    
    # Create a new file for each script
    file_path = os.path.join(GENERATED_CODE_FOLDER, f"generated_code_{int(time.time())}.py")
    with open(file_path, 'w') as code_file:
        code_file.write(code)
        print(f"Generated code saved to {file_path}")

def execute_python_code(code):
    try:
        if "import" in code:
            for line in code.splitlines():
                if line.startswith("import"):
                    module_name = line.split(" ")[1]
                    install_module(module_name)

        if not check_for_incomplete_code(code):
            print("The code contains unterminated strings or braces. Retrying the same prompt automatically...")
            return False

        code = fix_incomplete_code(code)
        code = add_function_call(code)

        # Execute the code safely
        exec(code)

        # If execution is successful, save the code
        save_generated_code(code)
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

            # Handle ethical rejection by ChatGPT
            new_prompt = handle_ethics_rejection(response, user_input)
            if new_prompt:
                user_input = new_prompt  # Prefill the prompt with the suggestion
                print(f"Prefilled new prompt: {user_input}")
                break

            # Check for and install any necessary modules mentioned in the ChatGPT response
            install_from_chatgpt_response(response)

            # Check if the response contains Python code and attempt to execute it
            if '```python' in response and '```' in response:
                code = response.split('```python')[1].split('```')[0]
                print("\nExtracted Python Code:\n", code)

                print("\nExecuting Python code...\n")
                success = execute_python_code(code)

                if success:
                    # Ask the user if they want to continue or exit
                    user_input = input("\nExecution successful! Do you want to continue? (yes/no): ").lower()
                    if user_input == 'no':
                        print("Exiting the interaction. Goodbye!")
                        exit()
                    else:
                        print("Continuing the interaction.")
                        break  # Continue to next prompt
            else:
                print("No Python code to execute.")
                break

            retry_count += 1
            if retry_count < RETRY_LIMIT:
                print(f"\nRetrying the same prompt in 3 seconds... (Attempt {retry_count}/{RETRY_LIMIT})")
                time.sleep(3)
            else:
                print(f"Exceeded retry limit of {RETRY_LIMIT}. Unable to get a complete code response.")
                break
