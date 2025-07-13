from flask import Flask, render_template, request, jsonify
import json
import os
import openai
import re
from dotenv import load_dotenv

app = Flask(__name__)

# OpenAI API Key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Paths to uploaded JSON files
JSON_FILES = {
    "IPC (Indian Penal Code)": "laws\ipc.json",
    "HMA (Hindu Marriage Act)": "laws\hma.json",
    "CPC (Code of Civil Procedure)": "laws\cpc.json",
    "CRPC (Code of Criminal Procedure)": "laws\crpc.json",
    "IDA (Indian Divorce Act)": "laws\ida.json",
    "IEA (Indian Evidence Act)": "laws\iea.json",
    "MVA (Motor Vehicles Act)": "laws\MVA.json",
    "NIA (Negotiable Instruments Act)": "laws\mia.json"
}

def load_json(file_path):
    """
    Loads JSON data from a file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        return []

def fetch_relevant_laws(query):
    """
    Searches all JSON files for relevant sections.
    """
    results = []
    
    for law_name, file_path in JSON_FILES.items():
        data = load_json(file_path)
        
        for section in data:
            sec_num = section.get("Section") or section.get("section")
            sec_title = section.get("section_title") or section.get("title")
            sec_desc = section.get("section_desc") or section.get("description")
            
            if query.lower() in (sec_title or "").lower() or query.lower() in (sec_desc or "").lower():
                results.append({
                    "law": law_name,
                    "section": sec_num,
                    "title": sec_title,
                    "description": sec_desc
                })

    return results

def split_sentences(text):
    """
    Splits text into sentences for better readability.
    """
    return re.split(r'(?<=[.!?]) +', text)

def get_legal_advice(question):
    """
    Retrieves relevant law sections first. If none found, queries OpenAI.
    """
    laws = fetch_relevant_laws(question)

    if laws:
        law_texts = [
            f"{law['law']} - Section {law['section']}: {law['title']} - " + " ".join(split_sentences(law['description']))
            for law in laws
        ]
        return law_texts, laws

    prompt = f"Provide legal advice based on Indian law for the following question: {question}"
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a legal expert in Indian law."},
                      {"role": "user", "content": prompt}],
            temperature=0.5
        )

        ai_response = response.choices[0].message.content
        return split_sentences(ai_response), []

    except Exception as e:
        return [f"Error: {str(e)}"], []

@app.route('/')
def home():
    return render_template('index.html', json_files=JSON_FILES.keys())

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    advice, laws = get_legal_advice(question)
    return jsonify({"answer": advice, "laws": laws})

@app.route('/view-json', methods=['POST'])
def view_json():
    """
    Returns the contents of a selected JSON law file in a formatted way.
    """
    data = request.get_json()
    selected_law = data.get("law")
    
    if selected_law not in JSON_FILES:
        return jsonify({"error": "Invalid law selection"}), 400
    
    laws_data = load_json(JSON_FILES[selected_law])
    
    # Convert to structured format
    formatted_laws = [
        f"<strong>Section {law.get('section', 'N/A')} - {law.get('title', 'No Title')}</strong>:<br>{law.get('description','No description')}"
        for law in laws_data
    ]
    
    return jsonify({"formatted": formatted_laws})


if __name__ == '__main__':
    app.run(debug=True)
