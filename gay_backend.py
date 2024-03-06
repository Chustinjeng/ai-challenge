from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

openai.api_key = "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"

@app.route('/sendMessage/<str:message>', methods=['PUT'])

def sendMessage(message):
    pass