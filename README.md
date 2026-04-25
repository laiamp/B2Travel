# B2Travel – Your Memory Universe 🌌✈️

Welcome to **B2Travel**, a next-generation AI-powered Memory Universe built for **HackUPC 2026**. 

B2Travel changes how you save, organize, and experience your travel inspirations. Instead of losing your favorite destinations in a messy camera roll or scattered browser bookmarks, B2Travel automatically organizes them using advanced Semantic AI and projects them into a fully immersive, interactive 3D VR environment.

## 🚀 Features

- **Chrome Extension "B2Travel Saver"**: Seamlessly right-click and save any image or text from travel sites (like Skyscanner) straight to your Memory Board.
- **AI-Powered Semantic Clustering**: No manual tagging needed! Our backend utilizes **OpenAI's CLIP Model** to extract 512-dimensional semantic embeddings from your images. Snow mountains group with snow mountains, and sunny beaches automatically group with other beaches.
- **UMAP 3D Projection**: We use UMAP (Uniform Manifold Approximation and Projection) to squash high-dimensional semantic spaces down into a visual 3D coordinate system.
- **Immersive WebVR Experience**: Built with A-Frame, B2Travel renders your saved destinations in a beautiful, interactive Virtual Reality "Memory Universe." Look around, use gaze-based interactions, and travel through your memories straight from your phone or VR headset.
- **Conversational Voice AI Agent**: Integrated with **ElevenLabs Conversational AI**, you can speak directly to a VR voice assistant. Say "Take me to a summer beach," and the AI dynamically calculates the semantic coordinates and visually guides you through the VR space to that exact vibe!
- **Multi-Modal Recommendations**: Select photos you like in VR by looking at them, and the frontend instantly beams the base64 images to your Voice Agent to provide personalized travel recommendations.

## 🏗️ Architecture (End-to-End Pipeline)

1. **Input (Chrome Extension)**: Click/Save an image or text while browsing.
2. **Backend (FastAPI)**: Receives the data and runs it through the `CLIP-ViT` model to generate embeddings.
3. **Storage (MongoDB)**: Stores the base64 images, text, and vector embeddings.
4. **Dimension Reduction (UMAP)**: The `/coordinates/` endpoint dynamically maps all vectors to 3D space.
5. **Presentation (A-Frame / CodePen)**: A frontend WebXR interface fetches coordinates and images, rendering them into a beautiful, explorable VR galaxy.
6. **Multi-Modal AI Interaction (ElevenLabs)**: A Python agent (`agent/main.py`) continuously listens to the user's voice. When the user asks for a vibe, it posts to `/coordinates/direction`, which emits a real-time event that the VR frontend polls and reacts to, actively guiding the user.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, PyTorch, HuggingFace Transformers (CLIP), UMAP-learn
- **Voice AI Agent**: ElevenLabs Conversational AI API
- **Database**: MongoDB (Atlas)
- **Frontend**: A-Frame (WebVR/WebXR), HTML5, Vanilla JS, CSS
- **Tools**: Chrome Extension APIs, ngrok (for tunneling localhost to mobile VR)

## 🏃 How to Run Locally

### 1. Start the Backend
Make sure you have Python 3.12+ and `uv` installed.
```bash
cd backend
# Create a .env file with MONGODB_URL and SKYSCANNER_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

### 2. Install Chrome Extension
- Open Chrome and navigate to `chrome://extensions/`
- Enable **Developer mode**
- Click **Load unpacked** and select the `/chrome_extension` folder.
- Pin the extension and start right-clicking images to save them to B2Travel!

### 3. Start the VR Frontend
To view your gallery on your computer:
```bash
cd frontend
python3 -m http.server 3000
```
Visit `http://localhost:3000/b2travel.html` to see the VR gallery.

*(To view on a mobile VR headset, use `ngrok` to expose the backend on port 8000, update the `BACKEND` URL in `b2travel.html`, and load the HTML on CodePen or a hosted server!)*

### 4. Start the Voice AI Agent (Optional)
To interact with the VR universe using your voice:
```bash
cd agent
# Create a .env file with ELEVENLABS_API_KEY
uv run python main.py
```
*(Speak into your microphone: "I want a summer vibe", and watch the VR frontend guide you to the beach!)*

---

*Built with ❤️ at HackUPC 2026*