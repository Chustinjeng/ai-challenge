# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from flask import Flask, render_template, request, json
from flask_socketio import SocketIO
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForPreTraining, BitsAndBytesConfig
from huggingface_hub import login
import google.generativeai as palm
import googlemaps
# import geocoder


maps_api_key = "AIzaSyA-y8gFhyief2fOiNBfDo_pTmPhtpkQby4"
maps_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={maps_api_key}"
gmaps = googlemaps.Client(key=maps_api_key)

palm_api_key = "AIzaSyAL1kGbBzgVKoVOZ6fhSL8qN9GKeBNpoA0"
palm.configure(api_key=palm_api_key)  # set API key

chroma_client = chromadb.PersistentClient(path="../chromadb")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
app = Flask(__name__)
# def get_current_location():
#     g = geocoder.ip('me')

#     return g.latlng

def get_location(location):
    geocode_result = gmaps.geocode(location)[0]
    northeast_lat = geocode_result['geometry']['bounds']['northeast']['lat']
    northeast_lng = geocode_result['geometry']['bounds']['northeast']['lng']
    southwest_lat = geocode_result['geometry']['bounds']['southwest']['lat']
    southwest_lng = geocode_result['geometry']['bounds']['southwest']['lng']
    center_lat = (southwest_lat + northeast_lat) / 2
    center_lng = (southwest_lng + northeast_lng) / 2
    return center_lat, center_lng

print(get_location('Jurong, Singapore'))

# current latitude and longitude of user
# latitude, longitude = get_current_location()
UNRELATED_PROMPT = "Please type in a prompt that is related to food!"
# tokenizer = AutoTokenizer.from_pretrained("zanelim/singbert-large-sg")
# model = AutoModelForPreTraining.from_pretrained("zanelim/singbert-large-sg")
# model_name_or_path = "google/gemma-7b"
# # To use a different branch, change revision
# # For example: revision="main"
# quantization_config = BitsAndBytesConfig(load_in_4bit=True)

# tokenizer = AutoTokenizer.from_pretrained("google/gemma-7b")
# model = AutoModelForCausalLM.from_pretrained("google/gemma-7b", quantization_config=quantization_config)

def parse_json(json_file):
    halal_attributes = []
    beverage_attributes = []
    soup_attributes = []
    seafood_attributes = []
    healthy_attributes = []
    fast_food_attributes = []
    local_attributes = []
    country_attributes = []

    for key, value in json_file.items():
        if key == "halal":
            if value == "True" or value == "False":
                halal_attributes.append(value)
            else:
                halal_attributes.extend(["True", "False"])

        if key == "beverage":
            if value == "True" or value == "False":
                beverage_attributes.append(value)
            else:
                beverage_attributes.extend(["True", "False"])

        if key == "soup":
            if value == "True" or value == "False":
                soup_attributes.append(value)
            else:
                soup_attributes.extend(["True", "False"])

        if key == "seafood":
            if value == "True" or value == "False":
                seafood_attributes.append(value)
            else:
                seafood_attributes.extend(["True", "False"])

        if key == "healthy":
            if value == "True" or value == "False":
                healthy_attributes.append(value)
            else:
                healthy_attributes.extend(["True", "False"])

        if key == "fast food":
            if value == "True" or value == "False":
                fast_food_attributes.append(value)
            else:
                fast_food_attributes.extend(["True", "False"])

        if key == "local":
            if value == "True" or value == "False":
                local_attributes.append(value)
            else:
                local_attributes.extend(["True", "False"])

        
    countries = json_file["countries"]
    countries_list = countries.split(",")
    for country in countries_list:
        if "japan" in country.lower():
            country_attributes.append("japanese")
        if "korea" in country.lower():
            country_attributes.append("korean")
        if "thai" in country.lower():
            country_attributes.append("thai")
        if "western" in country.lower():
            country_attributes.append("western")
        if "viet" in country.lower():
            country_attributes.append("vietnamese")
        if "chinese" in country.lower():
            country_attributes.append("chinese")
        if "italian" in country.lower():
            country_attributes.append("italian")
        if "asian" in country.lower():
            country_attributes.append("asian")
        if "malaysia" in country.lower():
            country_attributes.append("malaysian")
        if "indonesia" in country.lower():
            country_attributes.append("indonesian")
        if "india" in country.lower():
            country_attributes.append("indian")


    return halal_attributes, beverage_attributes, soup_attributes, seafood_attributes, healthy_attributes, fast_food_attributes, local_attributes, country_attributes



@app.route('/')

def home():
    #return 'Hello World'
    return render_template('index.html')

# @app.route('/get-collections', methods=['POST'])
# def get_collections():
#     collection_string = str(chroma_client.list_collections())
#     print("collection_string: ", collection_string)
#     collection_string = collection_string.replace("Collection(name=","")
#     collection_string = collection_string.replace("[","")
#     collection_string = collection_string.replace("]","")
#     collection_string = collection_string.replace(")","")
#     collections = collection_string.split()
#     return json.dumps(collections)

@app.route('/intermediate_query', methods=['POST'])
def intermediate_query():
    query = request.form.getlist('query')[0]
    prompt_template = f'''[INST] <<SYS>>

    You will be given a prompt that is either related to food or not related to food. 

    If the given prompt is not related to food, please respond in the following message:
    "Please type in a prompt that is related to food!"

    You will have to seive out the characteristics of food that is relevant to the prompt. 
    These characteristics include "halal", "beverage", "soup", "seafood", "healthy", "fast food" and "local".

    If the given prompt is related to food, please list out the characteristics that are most relevant to the prompt. 
    If the user gives a specific type of cuisine, that he/she wants to eat, you must include it in the response as well. 
    For example, Japanese cuisine, Korean cuisine, Western cuisine, Thailand cuisine amongst many others.

    Example 1:
    Prompt: I like to play sports.
    Expected response: Please type in a prompt that is related to food!
    Reason: The above prompt is not related to food, so we should give the response as expected.

    Example 2:
    Prompt: I have a sore throat, what should I eat?
    Expected response: soup, healthy, no fast food
    
    Reason: The user has a sore throat, so the user should consider soup or healthy options, but the user should not consider fast food options.

    Example 3:
    Prompt: I want to eat western food, what should I eat?
    Expected response: Western
    
    Reason: The user wants to eat western food, but the user did not mention any other characteristics, so the user should only consider western food options, and there should not be any other characteristics in the response.

    Example 4:
    Prompt: I want to eat fried western food, what should I eat?
    Expected response: not healthy, Western

    Reason: The user wants to eat fried western food, so the user should not consider healthy options. Since the user specifically said that he/she wants to eat western food, you also output "Western" in the response.

    Example 5:
    Prompt: I want to eat local halal food.
    Expected response: local, halal
    
    Reason: The user wants to eat local halal food, so the user should consider local options and halal options. 
    <</SYS>>
    {query} [/INST]
    '''
    response = palm.generate_text(model='models/text-bison-001', prompt=prompt_template, temperature=0.1)  # get response from Google's PaLM API
    return response.result
    

@app.route('/query', methods=['POST'])
def query():
    query =  request.form.getlist('query')[0]
    collection =  request.form.getlist('collection')[0]
    print("can get")
    print(query)
    if query != UNRELATED_PROMPT:

        prompt_template = f'''[INST] <<SYS>>
        You are an experienced food nutritionist in Singapore. Given a prompt that lists a user's food preference and/or health conditions, output a response in JSON format as follows:
            {{
                "halal": "True / False / Any", 
                "beverage": "True / False / Any", 
                "soup": "True / False / Any", 
                "seafood": "True / False / Any", 
                "healthy": "True / False / Any", 
                "fast food": "True / False / Any", 
                "local": "True / False / Any", 
                "countries": "<List all countries here>",
                "characteristics": "<Output the characteristics here>"
            }}

        You MUST output the response in such a format as shown above.
        You are based in Singapore, so any food that is not Singaporean food is NOT local food.

        Example 1: 
        Prompt: soup, healthy, no fast food

        Expected output: 
                {{
                    "halal": "Any", 
                    "beverage": "Any", 
                    "soup": "True", 
                    "seafood": "Any", 
                    "healthy": "True", 
                    "fast food": "False", 
                    "local": "Any", 
                    "countries": "",   
                    "characteristics": "Soup, healthy, no fast food"      
                }}

        Reason: Because the prompt says soup, healthy and no fast food, you can put True for "soup" and "healthy", and False for "fast food". 
                No countries were mentioned, so you leave the "countries" part with an empty string "".
                You output "Soup, healthy, no fast food" for the "characteristics" part because it is in the prompt.
                No other categories were mentioned, so you output "Any" for the rest of the categories.


        Example 2: 
        Prompt: Western

        Expected output: 
                {{
                    "halal": "Any", 
                    "beverage": "Any", 
                    "soup": "Any", 
                    "seafood": "Any", 
                    "healthy": "Any", 
                    "fast food": "Any", 
                    "local": "False", 
                    "countries": "Western",   
                    "characteristics": "Western"      
                }}

        Reason: Because the prompt only says Western food, you can output "Western" for the "countries" part. You output False for "local" because Western food is not local food.
                You output "Western" for the characteristics part because "Western" is in the prompt.
                No other categories were mentioned, so you output "Any" for the rest of the categories.
        
        Example 3:
        Prompt: not healthy, Japanese

        Expected output:
                {{
                    "halal": "Any", 
                    "beverage": "Any", 
                    "soup": "Any", 
                    "seafood": "Any", 
                    "healthy": "False", 
                    "fast food": "Any", 
                    "local": "False", 
                    "countries": "Japanese",  
                    "characteristics": "not healthy, Japanese"
                }}

        Reason: Because the prompt says not healthy and Japanese food, you can put False for "healthy" and "local". You output False for "local" because Japanese food is not local food.
                You output "Japanese" for the countries part because "Japanese" is in the prompt.
                You output "not healthy, Japanese" for the "characteristics" part because it is in the prompt.
                No other categories were mentioned, so you output "Any" for the rest of the categories.

        Again, you are based in Singapore, so any food that is not Singaporean food is NOT local food. Food that is not in Singapore is NOT local food. 
        For example, German food, Italian food, Thai food, Korean food, Vietnamese food, Japanese food, Western food amongst many others are NOT local food. You MUST output "local": "False" in the response.

        Note that soup and fast food do not go together. 
        For example, if "soup" is "True", "fast food" cannot be "True".

        <</SYS>>
        {query} [/INST]
        '''
        response = palm.generate_text(model='models/text-bison-001', prompt=prompt_template, temperature=0.1).result.strip().replace("```json", "")  # get response from Google's PaLM API
        print(response)
        response_json = json.loads(response)
        halal_filter, beverage_filter, soup_filter, seafood_filter, healthy_filter, fast_food_filter, local_filter, country_filter = parse_json(response_json)
        print(halal_filter)
        print(beverage_filter)
        print(soup_filter)
        print(seafood_filter)
        print(healthy_filter)
        print(fast_food_filter)
        print(local_filter)

        print(response_json)
        new_prompt = response_json["characteristics"]
        print(new_prompt)
        
    else:
        chroma_collection = chroma_client.get_collection(name=collection, embedding_function=sentence_transformer_ef)
        results = chroma_collection.query(query_texts=[query], n_results=10)
        retrieved_documents = [results['metadatas'], results['documents']]
        return retrieved_documents
        
    print(collection)
    chroma_collection = chroma_client.get_collection(name=collection, embedding_function=sentence_transformer_ef)
    if len(country_filter) == 0:
        results = chroma_collection.query(query_texts=[new_prompt], n_results=10,
                                       where={"$or": [{"halal": {"$in": halal_filter}},
                                                       {"beverage": {"$in": beverage_filter}},
                                                       {"soup": {"$in": soup_filter}},
                                                       {"seafood": {"$in": seafood_filter}},
                                                       {"healthy": {"$in": healthy_filter}},
                                                       {"fast food": {"$in": fast_food_filter}},
                                                       {"local": {"$in": local_filter}}]})
    else:
        results = chroma_collection.query(query_texts=[new_prompt], n_results=10,
                                       where={"$or": [{"halal": {"$in": halal_filter}},
                                                       {"beverage": {"$in": beverage_filter}},
                                                       {"soup": {"$in": soup_filter}},
                                                       {"seafood": {"$in": seafood_filter}},
                                                       {"healthy": {"$in": healthy_filter}},
                                                       {"fast food": {"$in": fast_food_filter}},
                                                       {"local": {"$in": local_filter}}]})
    # print(results)
    retrieved_documents = [results['metadatas'], results['documents']]
    print(retrieved_documents)
    # print("METADATA: ", results['metadatas'])
    return retrieved_documents

@app.route('/synthesize-response', methods=['POST'])
def synthesize_response():
    query = request.form.getlist('query')[0]
    if query == UNRELATED_PROMPT:
        return query
    context = request.form.getlist('documents')[0]
    initial_query = request.form.getlist('initial_query')[0]
    print("query")
    print(initial_query)
    print("context")
    print(context)
    
    prompt = f"{initial_query} [SEP] {context}"
    prompt_template=f'''[INST] <<SYS>>
            
    You are an experienced food blogger and nutritionist in Singapore. Respond to user prompts using only the information given. 

    Given a prompt that contains the types of food a user would like to eat and the list of potential restaurants in Singapore that is separated by a new line, give a response that includes the list of restaurants given in the prompt. 
    In your introduction, you have to explain why you choose the types of food that you output. You need to do this in an extremely polite tone.
    You should give an extra sentence of description of each restaurant that you output.
    If you have other restaurants that you want to recommend that is outside of the list of restaurants provided in the prompt, you have to recommend them in the response.

    Because you are a nutritionist, you need to give some medical advice to users who are suffering from a certain health condition. You need to let them know what food they should eat, or what food they should cut down on.
    After giving the users the restaurants, you would have to give some further medical advice as mentioned above.

    You MUST always answer in HTML markdown formatting. You will be penalized if you do not answer with HTML markdown when it would be possible. The HTML markdown formatting you support: headings, bold, italic, links, tables, lists, code blocks, and blockquotes.
    Example:
    For new lines or '\n', replace with the html element, <br />
    For bullet points and lists, return them in the following format:
        <li>text1</li>
        <li>text2</li>
        <li>text3</li>
    For bold items:
        <b>text to be bolded</b>
    For underlined items: 
        <u>text to be underlined</u>

    Remember to answer in HTML markdown formatting! Do NOT use symbols like * or ** in your answer, otherwise you will be penalized.
    <</SYS>>
    {prompt}[/INST]
    '''
    
    # input_ids = tokenizer(prompt_template, return_tensors='pt')
    # # input_ids = tokenizer(prompt_template, return_tensors='tf')

    # output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
    # output = model(input_ids)
    response = palm.generate_text(model='models/text-bison-001', prompt=prompt_template, temperature=0.1)  # get response from Google's PaLM API

    # output = replicate.run()
    # response = tokenizer.decode(output[0])
    # clean_response = response.split('[/INST]')[-1]
    print(response.result)
    return response.result
    
# main driver function
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
    # socketio.run(app, host="0.0.0.0", debug=True)
    


    # For example:
    # User prompt: 
    #     If you want to eat something light, you can consider the following options:
    #     - healthy: true
    #     - fast food: false
    #     - soup: true
    #     [SEP]
    #     The Soup Spoon Union - Hillion Mall
    #     Ding Ding Fish Soup & Ban Mian - Albert Centre
    #     Subway - Seletar Mall

    # Expected response:
    #     Light food options:
    #     - The Soup Spoon Union - Hillion Mall
    #         - The Soup Spoon is a restaurant that serves mainly soupy dishes.
    #     - Ding Ding Fish Soup & Ban Mian - Albert Centre
    #     - Subway - Seletar Mall
    #         - Subway is a fast-food chain that serves healthy sandwiches

    #     You can also consider other restaurant options:
    #     - The Daily Cut
    #     - Project Acai

    # Reason:
    # Because you are a given a prompt containing the user's food preferences and the list of potential restaurants, you should output them in a list format as shown above.
    # As mentioned, you are welcomed to give description of the restaurants.
    # You are also welcomed to give other restaurant options that are not in the user prompt.