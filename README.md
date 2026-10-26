# Emotion-Based Music Player 🎵

An emotion-aware music player that uses real-time facial emotion recognition to automatically play music based on the user's detected emotional state.

---

## Overview

This project combines computer vision and emotion analysis to create a personalized music listening experience. Using a webcam feed, the application detects the user's facial expression, classifies the emotion, and automatically plays music associated with the detected mood.

The application features an interactive Streamlit interface for real-time emotion detection and music playback.

---

## Features

- Real-time facial emotion detection using webcam input
- Emotion analysis using DeepFace
- Interactive user interface built with Streamlit
- Automatic music playback based on detected emotions
- Personalized listening experience
- Simple and intuitive workflow

---

## Tech Stack

### Language
- Python

### Libraries & Frameworks
- Streamlit
- OpenCV
- DeepFace

### Components
- Webcam Input
- Local Audio Playback

---

## How It Works

1. Launch the Streamlit application.
2. Capture live video through the webcam.
3. Process video frames using OpenCV.
4. Analyze facial expressions using DeepFace.
5. Detect the user's emotion.
6. Automatically play music corresponding to the detected emotion.

---

## Supported Emotions

The application can detect emotions such as:

- Happy
- Sad
- Angry
- Neutral
- Surprise
- Fear

> Supported emotions may vary depending on the DeepFace model being used.

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/emotion-based-music-player.git
cd emotion-based-music-player
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
streamlit run app.py
```

---

## Project Structure

```text
emotion-based-music-player/
│
├── app.py
├── requirements.txt
├── music/
├── assets/
└── README.md
```

## Screenshots

<img width="599" height="390" alt="image" src="https://github.com/user-attachments/assets/7ca345d9-021f-486d-9602-c54ab207360f" />

<img width="551" height="904" alt="image" src="https://github.com/user-attachments/assets/1b00b23c-f5be-4bd3-8ea3-725e81457991" />

