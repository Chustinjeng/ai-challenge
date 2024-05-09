# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import math
import googlemaps
import google.generativeai as palm
from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForPreTraining, BitsAndBytesConfig
from chromadb.utils import embedding_functions
from chromadb.config import Settings
import chromadb
from flask_socketio import SocketIO
from flask import Flask, render_template, request, json
import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
# import geocoder


maps_api_key = "AIzaSyA-y8gFhyief2fOiNBfDo_pTmPhtpkQby4"
maps_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={maps_api_key}"
gmaps = googlemaps.Client(key=maps_api_key)

palm_api_key = "AIzaSyAL1kGbBzgVKoVOZ6fhSL8qN9GKeBNpoA0"
palm.configure(api_key=palm_api_key)  # set API key

chroma_client = chromadb.PersistentClient(path="chromadb")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2")
app = Flask(__name__)


def get_location(location):
    """
    Gets the approximate latitude and longitude of a particular place in Singapore
    """
    geocode_result = gmaps.geocode(location)[0]
    print(geocode_result)
    latitude = geocode_result['geometry']['location']['lat']
    longitude = geocode_result['geometry']['location']['lng']

    return latitude, longitude

print(get_location("Jurong, Singapore"))

def get_range(lat, lon, radius):
    """
    Get the range of latitudes and longitudes within a certain distance (in kilometers) 
    of a given latitude and longitude
    """
    lat_range = radius / 111.0  # 1 degree of latitude is approximately 111 kilometers
    # 1 degree of longitude varies with latitude
    lon_range = radius / (111.0 * math.cos(math.radians(lat)))
    return (lat - lat_range, lat + lat_range), (lon - lon_range, lon + lon_range)


# current latitude and longitude of user
# latitude, longitude = get_current_location()
UNRELATED_PROMPT = "Please type in a prompt that is related to food!"

def parse_json(json_file):
    """
    Returns the filters that we will search our metadata by.
    E.g. If "halal" is "Any", the filter for "halal" is "True" and "False". 
        If "halal" is "True", the filter will be "True", likewise for "False".
    """
    halal_attributes = []
    beverage_attributes = []
    soup_attributes = []
    seafood_attributes = []
    healthy_attributes = []
    fast_food_attributes = []
    local_attributes = []

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


    return halal_attributes, beverage_attributes, soup_attributes, seafood_attributes, healthy_attributes, fast_food_attributes, local_attributes


@app.route('/')
def home():
    # return 'Hello World'
    return render_template('index.html')


@app.route('/intermediate_query', methods=['POST'])
def intermediate_query():
    query = request.form.getlist('query')[0]
    # prompt engineering for the LLM to output characteristics of food
    prompt_template = f'''[INST] <<SYS>>

    You will be given a prompt that is either related to food or not related to food. 

    If the given prompt is not related to food, please respond in the following message:
    "Please type in a prompt that is related to food!"

    You will have to seive out the characteristics of food that is relevant to the prompt. 
    These characteristics include "halal", "beverage", "soup", "seafood", "healthy", "fast food" and "local".
    The user may or may not input a location in Singapore. 
    If the user inputs a location, you would have to identify and output the location.

    The format that you MUST follow when outputting the response is as follows:
    <Characteristics> [SEP] <Location>

    If the given prompt is related to food, please list out the characteristics that are most relevant to the prompt. 
    If the user gives a specific type of cuisine, that he/she wants to eat, you must include it in the response as well. 
    For example, Japanese cuisine, Korean cuisine, Western cuisine, Thailand cuisine amongst many others.
    If the user inputs a European cuisine (Greek, British etc.) or an American cuisine, you MUST generalize it to become Western cuisine.
    E.g. American food = Western 
        Greek food = Western
        British food = Western
        etc.

    Example 1:
    Prompt: I like to play sports.
    Expected response: Please type in a prompt that is related to food!
    Reason: The above prompt is not related to food, so we should give the response as expected.

    Example 2: 
    Prompt: I want to find/eat food.
    Expected response: nice food, healthy
    Reason: The user wants to eat food, but the user did not include any preference, so we should output "nice food" and "healthy" in the response.

    Example 3:
    Prompt: I have a sore throat, what should I eat? 
    Expected response: soup, healthy, no fast food [SEP] None
    
    Reason: The user has a sore throat, so the user should consider soup or healthy options, but the user should not consider fast food options.
            The user did NOT type a location that he/she wants to eat in, so you must type "None" after the separator [SEP].

    Example 4:
    Prompt: I want to eat western food, what should I eat at Clementi?
    Expected response: Western [SEP] Clementi
    
    Reason: The user wants to eat western food, but the user did not mention any other characteristics, so the user should only consider western food options, and there should not be any other characteristics of food.
            The user typed a location that he/she wants to eat in, which is "Clementi", so you must type "Clementi" after the separator [SEP].

    Example 5:
    Prompt: I want to eat fried American food, what should I eat? I would like to eat at Bishan.
    Expected response: fattening, Western [SEP] Bishan

    Reason: The user wants to eat fried western food, so the user should not consider healthy options. Since the user specifically said that he/she wants to eat Western food, you also output "Western" in the response.
            The user typed a location that he/she wants to eat in, which is "Bishan", so you must type "Bishan" after the separator [SEP].

    Example 6:
    Prompt: I want to eat American/Greek/British/Irish food near Clementi
    Expected response: Western [SEP] Clementi

    Reason: The user wants to eat American food, so the user should not consider healthy options. Since the user specifically said that he/she wants to eat American food, you also output "Western" in the response, as American food is generalized to "Western".
            The user typed a location that he/she wants to eat in, which is "Clementi", so you must type "Clementi" after the separator [SEP].
            
    Example 7:
    Prompt: I am at Serangoon Avenue 1 and I want to eat local halal food.
    Expected response: local, halal [SEP] Serangoon Avenue 1
    
    Reason: The user wants to eat local halal food, so the user should consider local options and halal options. 
            The user typed a location that he/she wants to eat in, which is "Serangoon Avenue 1", so you must type "Serangoon Avenue 1" after the separator [SEP].

    Example 8:
    Prompt: I am near NUS and I want to eat a cheat meal
    Expected response: fried, fast food, fattening [SEP] NUS
    
    Reason: The user wants to eat a cheat meal, which is the same as an unhealthy meal, so the user should consider fried food and fast food options which are fattening.
            You MUST type in fried, fast food and fattening in the output.
            The user typed a location that he/she wants to eat in, which is "NUS", so you must type "NUS" after the separator [SEP].

    For any prompt that involves unhealthy food, do NOT output "unhealthy" in the response. Instead, you MUST output "fattening" in the response.

    <</SYS>>
    {query} [/INST]
    '''
    response = palm.generate_text(model='models/text-bison-001', prompt=prompt_template,
                                  temperature=0.1)  # get response from Google's PaLM API
    return response.result


@app.route('/query', methods=['POST'])
def query():
    query_data = request.form.getlist('query')[0]
    print(query_data)
    # get the user query and the location where the user prefers
    query, initial_location = query_data.split('[SEP]')
    collection = request.form.getlist('collection')[0]
    print("can get")
    print(query)
    print("location", initial_location)
    if query != UNRELATED_PROMPT:
        # prompt engineering for LLM to output a string in json format

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

        Example 4:
        Prompt: Nice

        Expected output:
                {{
                    "halal": "Any", 
                    "beverage": "Any", 
                    "soup": "Any", 
                    "seafood": "Any", 
                    "healthy": "False", 
                    "fast food": "Any", 
                    "local": "Any", 
                    "countries": "",  
                    "characteristics": "nice"
                }}

        Reason: The only characteristic in the prompt is "nice"
                No country is mentioned in the prompt, so you output "" for countries
                You output "nice" for the "characteristics" part because it is in the prompt.
                No other categories were mentioned, so you output "Any" for the rest of the categories.

        Again, you are based in Singapore, so any food that is not Singaporean food is NOT local food. Food that is not in Singapore is NOT local food. 
        For example, German food, Italian food, Thai food, Korean food, Vietnamese food, Japanese food, Western food amongst many others are NOT local food. You MUST output "local": "False" in the response.

        Note that soup and fast food do not go together. 
        For example, if "soup" is "True", "fast food" cannot be "True".

        <</SYS>>
        {query} [/INST]
        '''
        response = palm.generate_text(model='models/text-bison-001', prompt=prompt_template,
                                      temperature=0.1).result.strip().replace("```json", "")  # get response from Google's PaLM API
        print(response)
        response = response.replace("[ANS]", "").replace("[Q]", "").strip()
        response_json = json.loads(response)
        halal_filter, beverage_filter, soup_filter, seafood_filter, healthy_filter, fast_food_filter, local_filter = parse_json(
            response_json)

        print(response_json)
        # the characteristics of the food is subsequently passed to the vector database for querying
        new_prompt = response_json["characteristics"]
        print(new_prompt)

    else:
        chroma_collection = chroma_client.get_collection(
            name=collection, embedding_function=sentence_transformer_ef)
        results = chroma_collection.query(query_texts=[query], n_results=10)
        retrieved_documents = [results['metadatas'], results['documents']]
        return retrieved_documents

    # get location through google maps
    location = initial_location.strip()
    modified_location = location + ", Singapore"
    # get latitude and longitude from the location specified by user
    location_lat, location_lng = get_location(modified_location)
    lat_range, lng_range = get_range(location_lat, location_lng, 2)
    print("coordinates range")
    print(lat_range, lng_range)
    lat_min, lat_max = lat_range # latitude range of 2km radius
    lng_min, lng_max = lng_range # longitude range of 2km radius

    print(collection)
    chroma_collection = chroma_client.get_collection(
        name=collection, embedding_function=sentence_transformer_ef)
    if location == "None":
        results = chroma_collection.query(query_texts=[new_prompt], n_results=5,
                                          where={"$and": [
                                              {"halal": {"$in": halal_filter}},
                                              {"$or": [
                                                       {"beverage": {
                                                           "$in": beverage_filter}},
                                                       {"soup": {
                                                           "$in": soup_filter}},
                                                       {"seafood": {
                                                           "$in": seafood_filter}},
                                                       {"healthy": {
                                                           "$in": healthy_filter}},
                                                       {"fast food": {
                                                           "$in": fast_food_filter}},
                                                       {"local": {
                                                           "$in": local_filter}}]}]})
    else:
        # if location is specified, conduct metadata search on the calculated latitudes and longitudes
        results = chroma_collection.query(query_texts=[new_prompt], n_results=5,
                                          where={"$and": [{"longitude": {
                                              "$gte": lng_min
                                          }},
                                              {"longitude": {
                                                  "$lte": lng_max}},
                                              {"latitude": {
                                                  "$gte": lat_min}},
                                              {"latitude": {"$lte": lat_max}},
                                              {"halal": {"$in": halal_filter}},
                                              {"$or": [
                                                       {"beverage": {
                                                           "$in": beverage_filter}},
                                                       {"soup": {
                                                           "$in": soup_filter}},
                                                       {"seafood": {
                                                           "$in": seafood_filter}},
                                                       {"healthy": {
                                                           "$in": healthy_filter}},
                                                       {"fast food": {
                                                           "$in": fast_food_filter}},
                                                       {"local": {
                                                           "$in": local_filter}}]}]})
    retrieved_documents = [results['metadatas'], results['documents']]
    print(retrieved_documents)
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
    prompt_template = f'''[INST] <<SYS>>
            
    You are an experienced food blogger and nutritionist in Singapore. Respond to user prompts using only the information given. 

    Given a prompt that contains the types of food a user would like to eat and the list of potential restaurants in Singapore that is separated by a new line, give a response that includes the list of restaurants given in the prompt. 
    In your introduction, you have to explain why you choose the types of food that you output. You need to do this in an extremely polite tone.
    You should give an extra sentence of description of each restaurant that you output.
    If you have other restaurants that you want to recommend that is outside of the list of restaurants provided in the prompt, you have to recommend them in the response.

    Because you are a nutritionist, you need to give some medical advice to users who are suffering from a certain health condition. You need to let them know what food they should eat, or what food they should cut down on.
    After giving the users the restaurants, you would have to give some further medical advice as mentioned above.

    In your answer, do NOT use symbols like * or ** in your answer, otherwise you will be penalized.
    You MUST always answer in HTML formatting. You will be penalized if you do not answer with HTML when it would be possible. The HTML formatting you support: headings, bold, italic, links, tables, lists, code blocks, and blockquotes.
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

    Remember to answer in HTML formatting! Do NOT use symbols like * or ** in your answer, otherwise you will be penalized.
    <</SYS>>
    {prompt}[/INST]
    '''

   
    response = palm.generate_text(
        model='models/text-bison-001', prompt=prompt_template, temperature=0.1)

    print(response.result)
    return response.result


# main driver function
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
    # socketio.run(app, host="0.0.0.0", debug=True)

    