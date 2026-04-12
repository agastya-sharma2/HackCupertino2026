# from openai import OpenAI
# import json
# client = OpenAI(
#   base_url="https://openrouter.ai/api/v1",
#   api_key="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",
# )

# # First API call with reasoning
# inp = input("Enter your question: ")
# response = client.chat.completions.create(
#   model="arcee-ai/trinity-large-preview:free",
#   messages=[
#           {
#             "role": "user",
#             "content": inp
#           }
#         ],
#   extra_body={"reasoning": {"enabled": True}}
# )

# # Extract the assistant message with reasoning_details
# response = response.choices[0].message

# new = ""
# out = list(response)
# for i in out:
#     if i == "*":
#         new += " "
#     else:
#         new += i

# response = "".join(new)
# print(response)

# data = {response}
# with open('response.json', 'w') as f:
#     json.dump(data, f)

# z = open('response.json')
# data = json.load(z)

# print(data["response"]["food"])
# print(data["response"]["warm_up"])
# print(data["response"]["main_workout"])
# print(data["response"]["cool_down"])

# for p in data["response"]["plan"]:
#     print(p["food"])
#     print(p["duration"])
#     print(p["description"])

# z.close()

# new = ""
# for i in out:
#     if i == "*":
#         new += " "
#     else:
#         new += i

# response = "".join(new)
# print(response)

# data = {response}
# with open('response.json', 'w') as f:
#     json.dump(data, f)

# z = open('response.json')
# data = json.load(z)

# print(data["response"]["food"])
# print(data["response"]["warm_up"])
# print(data["response"]["main_workout"])
# print(data["response"]["cool_down"])

# for p in data["response"]["plan"]:
#     print(p["food"])
#     print(p["duration"])
#     print(p["description"])

# z.close()
from openai import OpenAI
import json
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# First API call with reasoning
prompt = input("Enter your question: ")
response = client.chat.completions.create(
  model="openai/gpt-oss-120b:free",
  messages=[
          {
            "role": "user",
            "content": '''
Assume the role of an expert athletic coach. Create a fitness and nutrition plan based on this request: {prompt}. 

Return ONLY a valid JSON object. Do not include introductory text, markdown code blocks (```), or citations outside the JSON. Use this exact structure:

{
  "response": {
    "food": "General nutritional summary",
    "warm_up": "Detailed warm-up instructions",
    "main_workout": "Detailed main workout instructions",
    "cool_down": "Detailed cool-down instructions",
    "plan": [
      {
        "food": "Specific item",
        "duration": "minutes",
        "description": "How to prepare/eat"
      }
    ],
    "sources": "List your expert sources here"
  }
}'''
          }
        ],
  extra_body={"reasoning": {"enabled": True}}
)

response = response.choices[0].message
print(response)
new = ""
out = list(response)
for i in out:
    if i == "*":
        new += " "
    else:
        new += i

response = "".join(new)
print(response)

data = {response}
with open('response.json', 'w') as f:
    json.dump(data, f)

z = open('response.json')
data = json.load(z)

print(data["response"]["food"])
print(data["response"]["warm_up"])
print(data["response"]["main_workout"])
print(data["response"]["cool_down"])

for p in data["response"]["plan"]:
    print(p["food"])
    print(p["duration"])
    print(p["description"])

z.close()

new = ""
for i in out:
    if i == "*":
        new += " "
    else:
        new += i

response = "".join(new)
print(response)

data = {response}
with open('response.json', 'w') as f:
    json.dump(data, f)

z = open('response.json')
data = json.load(z)

print(data["response"]["food"])
print(data["response"]["warm_up"])
print(data["response"]["main_workout"])
print(data["response"]["cool_down"])

for p in data["response"]["plan"]:
    print(p["food"])
    print(p["duration"])
    print(p["description"])

z.close()