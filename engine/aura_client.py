import google.generativeai as genai
import os

class AuraClient:
    """
    A client for interacting with Google's Gemini models.
    """
    def __init__(self, api_key=None, model_name="gemini-1.5-pro-latest"):
        """
        Initializes the AuraClient.

        Args:
            api_key: The Google AI API key. If not provided, it's read from
                     the GEMINI_API_KEY environment variable.
            model_name: The name of the Gemini model to use.
        """
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "API key for Gemini must be provided either as an argument or "
                "as a GEMINI_API_KEY environment variable."
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        print(f"AuraClient initialized with model: {model_name}")

    def send_prompt(self, prompt_text: str) -> str:
        """
        Sends a prompt to the Gemini model and gets a response.

        Args:
            prompt_text: The text prompt to send to the model.

        Returns:
            The model's response as a string, or None if an error occurred.
        """
        try:
            response = self.model.generate_content(prompt_text)
            return response.text
        except Exception as e:
            print(f"An error occurred while sending prompt to Gemini: {e}")
            return None

if __name__ == '__main__':
    # This is an example of how to use the client.
    # It requires the GEMINI_API_KEY environment variable to be set.
    # You can set it in a .env file in the project root.
    from dotenv import load_dotenv
    load_dotenv()

    try:
        # Using the default model gemini-1.5-pro-latest
        client = AuraClient() 
        
        # Example prompt
        prompt = "Explain the significance of the year 1991 in computer science."
        
        print(f"
Sending prompt: '{prompt}'")
        response_text = client.send_prompt(prompt)
        
        if response_text:
            print("
Response from Gemini:")
            print(response_text)
            
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
