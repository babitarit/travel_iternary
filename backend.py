import configparser
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from fpdf import FPDF
import google.generativeai as genai

# Load secrets from secret.properties
config = configparser.ConfigParser()

try:
    config.read('D:/Projects/MarchCohort/githubClone/travel_iternary/secret.properties')
    API_KEY = config.get('DEFAULT', 'API_KEY')  # Fetch API key
    SECRET_KEY = config.get('DEFAULT', 'SECRET_KEY')  # Fetch secret key
except (configparser.NoOptionError, configparser.NoSectionError) as e:
    print(f"Error reading configuration: {e}")
    exit(1)  # Exit if configuration is missing or incorrect

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY  # Use the loaded secret key for Flask sessions

CORS(app)  # Enable CORS for cross-origin requests

# Rest of your Flask app code...


class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "Travel Itinerary", align="C", ln=1)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", size=8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_day(self, day, content):
        self.set_font("Arial", style="B", size=12)
        self.cell(0, 10, f"Day {day}", ln=1)
        self.set_font("Arial", size=12)
        self.multi_cell(0, 10, content)

def generate_itinerary(source, destination, duration, budget, preferences):
    genai.configure(api_key=API_KEY)  # Use the loaded API key

    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""Create a detailed {duration}-day travel itinerary from {source} to {destination} 
    with a total budget of ₹{budget}. Preferences: {preferences}. 
    Include daily breakdowns with:
    - Morning/Afternoon/Evening activities
    - Budget allocations
    - Transportation options
    - Food suggestions
    - Cultural considerations
    Format with clear day-wise headings and bullet points."""
    
    try:
        response = model.generate_content([prompt])
        return response.text
    except Exception as e:
        print(f"Error generating itinerary: {e}")
        return None

def save_to_pdf(itinerary_text):
    # Replace unsupported Unicode characters with ASCII equivalents
    replacements = {
        "₹": "Rs.",  # Replace rupee symbol
        "–": "-",    # Replace en dash with a hyphen
        "—": "-",    # Replace em dash with a hyphen
        "“": '"',    # Replace left double quote with a standard quote
        "”": '"',    # Replace right double quote with a standard quote
        "‘": "'",    # Replace left single quote with a standard quote
        "’": "'",    # Replace right single quote with a standard quote
    }

    for unicode_char, ascii_char in replacements.items():
        itinerary_text = itinerary_text.replace(unicode_char, ascii_char)

    pdf = PDF()
    pdf.add_page()

    # Use default Arial font for output
    pdf.set_font("Arial", size=12)

    # Split text into days for formatting (assuming AI response is structured with "Day X" headings)
    days = itinerary_text.split("Day ")
    
    for i, day_content in enumerate(days[1:], start=1):  # Skip first split part before "Day X"
        pdf.add_day(i, f"Day {day_content.strip()}")

    pdf_file_path = "Travel_Itinerary.pdf"
    pdf.output(pdf_file_path)
    
    return pdf_file_path



last_itinerary = {"text": None, "pdf_path": None}

@app.route('/generate_itinerary', methods=['POST'])
def generate_itinerary_api():
    global last_itinerary

    data = request.json
    
    source = data.get('source')
    destination = data.get('destination')
    duration = data.get('duration')
    budget = data.get('budget')
    preferences = data.get('preferences')

    if not all([source, destination, duration, budget, preferences]):
        return jsonify({"error": "All fields (source, destination, duration, budget, preferences) are required."}), 400

    itinerary_text = generate_itinerary(source, destination, duration, budget, preferences)

    if itinerary_text:
        itinerary_text = itinerary_text.replace("₹", "Rs.")
        
        print("\nGenerated Itinerary:")
        print(itinerary_text)

        last_itinerary["text"] = itinerary_text
        last_itinerary["pdf_path"] = save_to_pdf(itinerary_text)  # Save PDF here

        return jsonify({"message": "Itinerary generated successfully!", "itinerary_text": itinerary_text}), 200
    
    return jsonify({"error": "Failed to generate itinerary."}), 500

@app.route('/get_last_itinerary', methods=['GET'])
def get_last_itinerary():
    global last_itinerary

    if not last_itinerary["text"]:
        return jsonify({"error": "No itinerary has been generated yet."}), 404

    return jsonify({
        "message": "Here is the last generated itinerary.",
        "itinerary_text": last_itinerary["text"],
        "pdf_file": last_itinerary["pdf_path"]
    }), 200

@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    global last_itinerary

    # Check if PDF path exists in memory
    if not last_itinerary.get("pdf_path"):
        return jsonify({"error": "No PDF has been generated yet."}), 404

    # Check if the file exists on disk
    pdf_path = last_itinerary["pdf_path"]
    try:
        return send_file(pdf_path, as_attachment=True), 200
    except FileNotFoundError:
        return jsonify({"error": "PDF file not found on server."}), 404
    except Exception as e:
        print(f"Error sending PDF: {e}")
        return jsonify({"error": "An unexpected error occurred while downloading the PDF."}), 500



if __name__ == '__main__':
    app.run(debug=True)
