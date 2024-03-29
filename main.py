import threading
from flask import Flask, Response
from flask import request as req
from flask_cors import CORS
import helpers.helper as helper
from helpers.provider import *
from memory.memory import Memory
m = Memory()
from transformers import AutoTokenizer
import extensions
from base64 import b64encode
from llms import gpt4,gpt4stream
import pyimgur
app = Flask(__name__)
CORS(app)
import queue

from functions import allocate,mm,ask,clear


@app.route("/v1/chat/completions", methods=['POST'])
def chat_completions2():
    helper.stopped=True

    streaming = req.json.get('stream', True)
    model = req.json.get('model', 'gpt-4-web')
    messages = req.json.get('messages')
    print(messages)
    functions = req.json.get('functions')
    print(functions)

    
    allocate(messages,helper.data, m.get_data('uploaded_image'),m.get_data('context'),helper.systemp,model)

    t = time.time()

    def stream_response(messages,model):
        helper.q = queue.Queue() # create a queue to store the response lines
        if  helper.stopped:
            helper.stopped = False
            print("No process to kill.")

        threading.Thread(target=gpt4stream,args=(messages,model)).start() # start the thread
        
        started=False
        while True: # loop until the queue is empty
            try:
                if 11>time.time()-t>10 and not started and  m.get_data('uploaded_image')!="":
                    yield 'data: %s\n\n' % json.dumps(helper.streamer("> Analysing this Image🖼️"), separators=(',' ':'))
                    time.sleep(2)
                elif 11>time.time()-t>10 and not started :
                    yield "WAIT"
                    time.sleep(1)  
                if 11>time.time()-t>10 and not started :
                    yield 'data: %s\n\n' % json.dumps(helper.streamer("> Please wait"), separators=(',' ':'))
                    time.sleep(2)
                elif time.time()-t>11 and not started :
                    yield 'data: %s\n\n' % json.dumps(helper.streamer("."), separators=(',' ':'))
                    time.sleep(1)
                elif time.time()-t>100 and not started:
                    yield 'data: %s\n\n' % json.dumps(helper.streamer("Timed out"), separators=(',' ':'))
                    break

                line = helper.q.get(block=False)
                if line == "END":
                    break
                if not started:
                    started = True
                    yield 'data: %s\n\n' % json.dumps(helper.streamer("\n\n"), separators=(',' ':'))

                yield 'data: %s\n\n' % json.dumps(helper.streamer(line), separators=(',' ':'))

                helper.q.task_done() # mark the task as done


            except helper.queue.Empty: 
                pass
            except Exception as e:
                print(e)

    if "/clear" in helper.data["message"]  :
        return 'data: %s\n\n' % json.dumps(helper.streamer('Cleared✅ '+clear()), separators=(',' ':'))
    
    elif "/log" in helper.data["message"]  :
        return 'data: %s\n\n' % json.dumps(helper.streamer(str(data)), separators=(',' ':'))

    elif "/prompt" in helper.data["message"]  :

        if helper.systemp == False:
            helper.systemp=True
        else:
            helper.systemp=False
        return 'data: %s\n\n' % json.dumps(helper.streamer(f"helper.Systemprompt is  {helper.systemp}"), separators=(',' ':'))

    elif "/help" in helper.data["message"]  :
        return 'data: %s\n\n' % json.dumps(helper.streamer(helper.about), separators=(',' ':'))
    
    if "/upload" in helper.data["message"] and "gpt-4" in model :
        return 'data: %s\n\n' % json.dumps(helper.streamer(helper.up), separators=(',' ':'))
    if "/context" in helper.data["message"] and "gpt-4" in model :
        return 'data: %s\n\n' % json.dumps(helper.streamer(helper.cont), separators=(',' ':'))
    if "/mindmap" in helper.data["message"] or "/branchchart" in helper.data["message"] or "/timeline" in helper.data["message"] :
        return app.response_class(extensions.grapher(helper.data["message"],model), mimetype='text/event-stream')
    
    elif "/flowchart" in helper.data["message"] or "/complexchart" in helper.data["message"] or  "/linechart" in helper.data["message"] :
        if "gpt-3" in model:
            if "/flowchart" in  helper.data["message"]:
                return app.response_class(stream_response([{"role": "system", "content": f"{flowchat}"},{"role": "user", "content": f"{data['message'].replace('/flowchart','')}"}],"gpt-3"), mimetype='text/event-stream')
            if "/complexchart" in  helper.data["message"]:
                return app.response_class(stream_response([{"role": "system", "content": f"{complexchat}"},{"role": "user", "content": f"{data['message'].replace('/complexchart','')}"}],"gpt-3"), mimetype='text/event-stream')
            if "/linechart" in  helper.data["message"]:
                return app.response_class(stream_response([{"role": "system", "content": f"{linechat}"},{"role": "user", "content": f"{data['message'].replace('/linechat','')}"}],"gpt-3"), mimetype='text/event-stream')
        elif "gpt-4" in model:

            if "/flowchart" in  helper.data["message"]:
                helper.data["message"]=helper.data["message"].replace("/flowchart","")
                helper.data["systemMessage"]=mermprompt.format(instructions=flowchat)
            if "/complexchart" in  helper.data["message"]:
                helper.data["message"]=helper.data["message"].replace("/complexchart","")
                helper.data["systemMessage"]=mermprompt.format(instructions=complexchat)

            if "/linechart" in  helper.data["message"]:
                helper.data["message"]=helper.data["message"].replace("/linechart","")
                helper.data["systemMessage"]=mermprompt.format(instructions=linechat)

            return app.response_class(stream_response(messages,"gpt-4"), mimetype='text/event-stream')




    if not streaming and "AI conversation titles assistant" in messages[0]["content"]:
        print("USING GPT_4 CONVERSATION TITLE")
        k=gpt4(messages,"gpt-3")
        print(k)
        return helper.output(k)
    elif not streaming :
        print("USING GPT_4 NO STREAM")
        k=gpt4(messages,model)
        print(k)
        return helper.output(k)
    if  streaming: 
        return app.response_class(stream_response(messages,model), mimetype='text/event-stream')







@app.route('/api/<name>')
def hello_name(name):
   url = "https://"+name+"/conversation"
   helper.api_endpoint=url
   return f'{helper.api_endpoint}'

@app.route('/context', methods=['POST'])
def my_form_post():
    text = req.form['text']
    m.update_data('context', text)
    m.save()
    return "The context has been added."

@app.route('/context')
def my_form():
    return '''
<form method="POST">
    <textarea name="text"></textarea>
    <input type="submit">
</form>
'''

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global img
    if req.method == 'POST': 
        if 'file1' not in req.files: 
            return 'there is no file1 in form!'
        client = pyimgur.Imgur("47bb97a5e0f539c")
        r = client._send_request('https://api.imgur.com/3/image', method='POST', params={'image': b64encode(req.files['file1'].read())})
        m.update_data('uploaded_image', r["link"])
        m.save()        
        print("image saved")
        return f"Image has been uploaded and your question can now be asked. ({r['link']})"

    return '''
    <h1>Upload new Image</h1>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file1">
      <input type="submit">
    </form>
    '''

def get_embedding(input_text, token):
    huggingface_token = helper.huggingface_token
    embedding_model = 'sentence-transformers/all-mpnet-base-v2'
    max_token_length = 500

    # Load the tokenizer for the 'all-mpnet-base-v2' model
    tokenizer = AutoTokenizer.from_pretrained(embedding_model)
    # Tokenize the text and split the tokens into chunks of 500 tokens each
    tokens = tokenizer.tokenize(input_text)
    token_chunks = [tokens[i:i + max_token_length]
                    for i in range(0, len(tokens), max_token_length)]

    # Initialize an empty list
    embeddings = []

    # Create embeddings for each chunk
    for chunk in token_chunks:
        # Convert the chunk tokens back to text
        chunk_text = tokenizer.convert_tokens_to_string(chunk)

        # Use the Hugging Face API to get embeddings for the chunk
        api_url = f'https://api-inference.huggingface.co/pipeline/feature-extraction/{embedding_model}'
        headers = {'Authorization': f'Bearer {huggingface_token}'}
        chunk_text = chunk_text.replace('\n', ' ')

        # Make a POST request to get the chunk's embedding
        response = requests.post(api_url, headers=headers, json={
                                 'inputs': chunk_text, 'options': {'wait_for_model': True}})

        # Parse the response and extract the embedding
        chunk_embedding = response.json()
        # Append the embedding to the list
        embeddings.append(chunk_embedding)

    # averaging all the embeddings
    # this isn't very effective
    # someone a better idea?
    num_embeddings = len(embeddings)
    average_embedding = [sum(x) / num_embeddings for x in zip(*embeddings)]
    embedding = average_embedding
    return embedding


@app.route('/embeddings', methods=['POST'])
def embeddings():
    input_text_list = req.get_json().get('input')
    input_text      = ' '.join(map(str, input_text_list))
    token           = req.headers.get('Authorization').replace('Bearer ', '')
    embedding       = get_embedding(input_text, token)
    
    return {
        'data': [
            {
                'embedding': embedding,
                'index': 0,
                'object': 'embedding'
            }
        ],
        'model': 'text-embedding-ada-002',
        'object': 'list',
        'usage': {
            'prompt_tokens': None,
            'total_tokens': None
        }
    }

@app.route('/')
def yellow_name():
   return f'Server 1 is OK and server 2 check: {helper.api_endpoint}'

@app.route("/v1/models")
def models():
    print("Models")
    return helper.model



if __name__ == '__main__':
    config = {
        'host': '0.0.0.0',
        'port': 1337,
        'debug': True
    }

    app.run(**config)
