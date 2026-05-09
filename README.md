<div align="center">
  
  # B2Travel – Your Memory Universe 🌌✈️

  **An AI-powered, Voice-Controlled Virtual Reality Travel Dashboard.**

  <br>
  
  ![HackUPC 2026](https://img.shields.io/badge/HackUPC_2026-Winner-blue?style=for-the-badge&logo=hackerearth)
  ![Skyscanner](https://img.shields.io/badge/Skyscanner_Challenge-2nd_Prize-00A698?style=for-the-badge)
  ![ElevenLabs](https://img.shields.io/badge/MLH_Best_Use_Of-ElevenLabs-black?style=for-the-badge)

  <br>

  [Demo Video](#-demo-video) •
  [Architecture](#%EF%B8%8F-architecture) •
  [Tech Stack](#-tech-stack) •
  [Installation](#-how-to-run-locally)

</div>

---

B2Travel revolutionizes how you save, organize, and experience travel inspirations. Instead of losing your favorite destinations in a messy camera roll or scattered browser bookmarks, B2Travel automatically organizes them using advanced Semantic AI and projects them into a fully immersive, interactive 3D VR environment. 

You don't just scroll through flights; you **speak to your AI Agent**, explore the semantic universe of your memories, and pull up real-time Skyscanner tickets seamlessly in VR.

---

## 🏆 HackUPC 2026 Awards
We are incredibly proud to have built B2Travel in 36 hours and taken home:
* 🥈 **2nd Prize: Skyscanner Challenge** (For seamless integration of the Skyscanner API into a radical new VR booking interface)
* 🎙️ **MLH Best Use of ElevenLabs** (For our deeply integrated, conversational Voice AI Agent that drives the entire 3D UI)

---

## 🎥 Demo Video

> **[🎥 Watch the full Demo Video on YouTube / Devpost here!]**

*(Add a high-quality GIF of the VR UI reacting to the Voice Agent here)*

---

## 🚀 Features

- **Conversational Voice AI Agent (ElevenLabs)**: A fully interactive VR voice assistant. Say *"Take me to a summer beach"*, and the AI dynamically calculates semantic coordinates, speaks to you, and visually guides you through the VR space to that exact vibe!
- **AI-Powered Semantic Clustering (CLIP)**: No manual tagging needed! Our backend utilizes **OpenAI's CLIP Model** to extract 512-dimensional semantic embeddings from your images. Snow mountains group with snow mountains, and sunny beaches automatically group with other beaches.
- **UMAP 3D Projection**: We use UMAP (Uniform Manifold Approximation and Projection) to squash high-dimensional semantic spaces down into a visual 3D coordinate system.
- **Immersive WebVR Experience**: Built with A-Frame, B2Travel renders your saved destinations in a beautiful, interactive Virtual Reality "Memory Universe." Look around, use gaze-based interactions, and travel through your memories straight from your phone or VR headset.
- **Skyscanner Booking in VR**: Select photos you like in VR by looking at them, and the frontend instantly beams the base64 images to your Voice Agent to provide personalized, real-time Skyscanner flight recommendations mapped to your origin city.
- **Chrome Extension "B2Travel Saver"**: Seamlessly right-click and save any image or text from travel sites straight to your Memory Board.

---

## 🏗️ Architecture (End-to-End Pipeline)

1. **Input (Chrome Extension)**: Click/Save an image or text while browsing.
2. **Backend (FastAPI)**: Receives the data and runs it through the `CLIP-ViT` model to generate embeddings.
3. **Storage (MongoDB)**: Stores the base64 images, text, and vector embeddings.
4. **Dimension Reduction (UMAP)**: The `/coordinates/` endpoint dynamically maps all vectors to 3D space.
5. **Presentation (A-Frame)**: A frontend WebXR interface fetches coordinates and images, rendering them into a beautiful, explorable VR galaxy.
6. **Multi-Modal AI Interaction (ElevenLabs)**: A Python agent (`agent/main.py`) continuously listens to the user. When the user asks for a vibe, it does a K-Nearest-Neighbor cosine similarity search in the high-dimensional CLIP space, returning coordinates that emit a real-time event. The VR frontend polls this and reacts, actively guiding the user.

---

## 🛠️ Tech Stack

- **Voice AI Agent**: ElevenLabs Conversational AI API
- **Backend**: Python, FastAPI, PyTorch, HuggingFace Transformers (CLIP), UMAP-learn
- **Database**: MongoDB (Atlas)
- **Frontend**: A-Frame (WebVR/WebXR), HTML5 Canvas, Vanilla JS, CSS
- **APIs**: Skyscanner API
- **Tools**: Chrome Extension APIs, ngrok (for tunneling localhost to mobile VR)

---

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

*(To view on a mobile VR headset, use `ngrok` to expose the backend on port 8000, update the `BACKEND` URL in `b2travel.html`, and load the HTML on your phone!)*

### 4. Start the Voice AI Agent
To interact with the VR universe using your voice:
```bash
cd agent
# Create a .env file with ELEVENLABS_API_KEY
uv run python main.py
```
*(Speak into your microphone: "I want a summer vibe", and watch the VR frontend guide you to the beach!)*

---

*Built with ❤️ at HackUPC 2026*