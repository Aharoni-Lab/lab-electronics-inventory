import openai


openai_client = openai.OpenAI(api_key="OpenAI secret key"
                              )

try:
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print("API Call Failed:", e)
