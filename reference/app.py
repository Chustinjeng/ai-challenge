# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import pysqlite3
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from flask import Flask, render_template, request, json
from flask_socketio import SocketIO
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel

chroma_client = chromadb.PersistentClient(path="../chromadb")

app = Flask(__name__)

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

@app.route('/query', methods=['POST'])
def query():
    query =  request.form.getlist('query')[0]
    collection =  request.form.getlist('collection')[0]
    print("can get")
    print(query)
    print(collection)
    chroma_collection = chroma_client.get_collection(name=collection)
    results = chroma_collection.query(query_texts=[query], n_results=10)
    retrieved_documents = [results['metadatas'], results['documents']]
    # print("METADATA: ", results['metadatas'])
    return retrieved_documents

@app.route('/synthesize-response', methods=['POST'])
def synthesize_response():
    query = request.form.getlist('query')[0]
    context = request.form.getlist('documents')[0]
    model_path = "../../codellamachat/text-generation-webui/models/TheBloke_CodeLlama-13B-Instruct-GPTQ-8bit-128g"
    model = AutoModelForCausalLM.from_pretrained(model_path).cuda()
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    prompt = f"{query} [SEP] {context}"
    prompt_template=f'''[INST] <<SYS>>
            
    You are an experienced food blogger in Singapore. Respond to user prompts using only the information given. 
    
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
    
    input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
    output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
    response = tokenizer.decode(output[0])
    clean_response = response.split('[/INST]')[-1]
    return clean_response
    
# main driver function
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
    # socketio.run(app, host="0.0.0.0", debug=True)
    