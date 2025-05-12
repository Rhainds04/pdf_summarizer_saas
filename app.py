from flask import Flask, request, render_template, redirect, jsonify
import fitz
import os
import json
from transformers import pipeline
from deep_translator import GoogleTranslator
from datetime import datetime

app = Flask(__name__)

summarizer = pipeline("summarization")

SAVE_FILE = "saved_summaries.json"

if not os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "w") as f:
        json.dump([], f)

@app.route("/", methods=["GET", "POST"])
def home():
    text = ""
    summary = ""
    saved_summaries = []  # Add this line to hold saved summaries

    # Load saved summaries for the sidebar
    with open(SAVE_FILE, "r") as f:
        saved_summaries = json.load(f)

    if request.method == "POST":
        pdf = request.files["pdf"]
        lang = request.form.get("lang", "en")  # Get selected language (default to English)

        if pdf:
            text = extract_text_from_pdf(pdf)
            summary = summarize_text(text)

            # Translate if needed
            if lang != "en":
                summary = GoogleTranslator(source="auto", target=lang).translate(summary)

        return render_template("index.html", text=text, summary=summary, saved_summaries=saved_summaries)

    return render_template("index.html", text="", summary="", saved_summaries=saved_summaries)


@app.route("/save", methods=["POST"])
def save_summary():
    summary = request.form.get("summary")
    text = request.form.get("text")

    if not summary or not text:
        return "Missing summary or text", 400

    save_data = {
        "id": datetime.now().isoformat(),
        "title": "Summary " + datetime.now().strftime("%H:%M:%S"),
        "text": text,
        "summary": summary
    }

    file_path = "saved_summaries.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            all_summaries = json.load(f)
    else:
        all_summaries = []

    all_summaries.append(save_data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2, ensure_ascii=False)

    return redirect("/")

@app.route("/summaries", methods=["GET"])
def get_summaries():
    with open(SAVE_FILE, "r") as f:
        summaries = json.load(f)
    return jsonify(summaries)

@app.route("/view/<summary_id>", methods=["GET"])
def view_summary(summary_id):
    # Load all summaries
    with open(SAVE_FILE, "r") as f:
        all_summaries = json.load(f)
    
    # Find the requested summary
    summary_data = None
    for summary in all_summaries:
        if summary.get("id") == summary_id:
            summary_data = summary
            break
    
    if not summary_data:
        return "Summary not found", 404
    
    # Pass the found summary data to the template
    return render_template("index.html", 
                          text=summary_data.get("text", ""), 
                          summary=summary_data.get("summary", ""),
                          saved_summaries=all_summaries,
                          viewing_saved=True,
                          current_summary=summary_data)

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text
    
def summarize_text(text):
    num_words = len(text.split())
    
    # Compute summary length: 1/5 of input size
    target_len = num_words // 5

    # Set bounds to avoid errors or nonsense output
    min_len = max(15, target_len // 2)       # at least 15 words, half of target
    max_len = min(300, target_len)           # cap max at 300 to respect model limits

    input_text = text[:3000]

    summary = summarizer(input_text, max_length=max_len, min_length=min_len, do_sample=False)
    return summary[0]['summary_text']

  
if __name__ == "__main__":
    app.run(debug=True)