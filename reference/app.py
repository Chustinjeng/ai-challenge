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
# import googlemaps
import geocoder


# maps_api_key = "AIzaSyA-y8gFhyief2fOiNBfDo_pTmPhtpkQby4"
palm_api_key = "AIzaSyAL1kGbBzgVKoVOZ6fhSL8qN9GKeBNpoA0"
# os.environ["REPLICATE_API_TOKEN"] = "r8_QBkNOdw2jq8CufXJjFIr1e2NgVnGqrK0KebKq"
# login()
palm.configure(api_key=palm_api_key)  # set API key

chroma_client = chromadb.PersistentClient(path="../chromadb")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
app = Flask(__name__)
def get_current_location():
    g = geocoder.ip('me')

    return g.latlng

# current latitude and longitude of user
latitude, longitude = get_current_location()

# tokenizer = AutoTokenizer.from_pretrained("zanelim/singbert-large-sg")
# model = AutoModelForPreTraining.from_pretrained("zanelim/singbert-large-sg")
# model_name_or_path = "google/gemma-7b"
# # To use a different branch, change revision
# # For example: revision="main"
# quantization_config = BitsAndBytesConfig(load_in_4bit=True)

# tokenizer = AutoTokenizer.from_pretrained("google/gemma-7b")
# model = AutoModelForCausalLM.from_pretrained("google/gemma-7b", quantization_config=quantization_config)

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

    There are some characteristics of food that you would have to output true or false to.
    These characteristics are: halal, beverage, soup, seafood, healthy, fast food, local.

    If the given prompt is related to food, please list out the characteristics that are most relevant to the prompt. 
    If the user gives a specific type of cuisine, that he/she wants to eat, do include it in the response as well.

    Example 1:
    Prompt: I like to play sports.
    Expected response: Please type in a prompt that is related to food!
    Reason: The above prompt is not related to food, so we should give the response as expected.

    Example 2:
    Prompt: I have a sore throat, what should I eat?
    Expected response: 
        If you have a sore throat, you can consider the following options:
        - soup: true
        - healthy: true
        - fast food: false
    
    Reason: The user has a sore throat, so the user should consider soup or healthy options, but the user should not consider fast food options.

    Example 3:
    Prompt: I want to eat western food, what should I eat?
    Expected response: 
        If you want to eat western food, you can consider the following options:
        - Western
    
    Reason: The user wants to eat western food, but the user did not mention any other characteristics, so the user should only consider western food options, and there should not be any other characteristics in the response.

    Example 4:
    Prompt: I want to eat fried western food, what should I eat?
    Expected response: 
        If you want to eat fried western food, you can consider the following options:
        - healthy: false
        - fast food: true
        - Western
    
    Reason: The user wants to eat fried western food, so the user should consider fast food options, but the user should not consider healthy options. Since the user specifically said that he/she wants to eat western food, you also output "Western" in the response.

    Example 5:
    Prompt: I want to eat local halal food.
    Expected response: 
        If you want to eat local halal food, you can consider the following options:
        - local: true
        - halal: true
    
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
    print(collection)
    chroma_collection = chroma_client.get_collection(name=collection, embedding_function=sentence_transformer_ef)
    results = chroma_collection.query(query_texts=[query], n_results=10)
    # print(results)
    retrieved_documents = [results['metadatas'], results['documents']]
    print(retrieved_documents)
    # print("METADATA: ", results['metadatas'])
    return retrieved_documents

@app.route('/synthesize-response', methods=['POST'])
def synthesize_response():
    query = request.form.getlist('query')[0]
    context = request.form.getlist('documents')[0]
    print("query")
    print(query)
    print("context")
    print(context)
    
    prompt = f"{query} [SEP] {context}"
    prompt_template=f'''[INST] <<SYS>>
            
    You are an experienced food blogger in Singapore. Respond to user prompts using only the information given. 

    Given a prompt that contains the types of food a user would like to eat and the list of potential restaurants in Singapore that is separated by a new line, give a response that includes the list of restaurants given in the prompt. 
    You should give an extra sentence of description of each restaurant that you output.
    If you have other restaurants that you want to recommend that is outside of the list of restaurants provided in the prompt, feel free to recommend them in the response.

    You always answer in HTML markdown formatting. You will be penalized if you do not answer with HTML markdown when it would be possible. The HTML markdown formatting you support: headings, bold, italic, links, tables, lists, code blocks, and blockquotes.
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