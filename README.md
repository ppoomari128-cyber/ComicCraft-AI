# ComicCraft AI

ComicCraft AI is an AI-powered comic story creator that generates a comic story and creates visual panels using Gemini AI models.

## Features

* Generate comic stories from user prompts
* Create multiple comic panels
* Generate AI images for the panels
* Display generated panels on a web page
* Simple and user-friendly interface
* Gemini AI integration

## Technologies Used

* Python
* Flask
* HTML
* CSS
* JavaScript
* Google Gemini API
* Pillow
* python-dotenv

## Project Structure

```text
ComicCraft/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   └── ...
│
├── static/
│   └── ...
│
├── templates/
│   └── ...
│
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Installation

### 1. Clone the project

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ComicCraft
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the API key

Create a `.env` file in the project root and add your Gemini API key:

```env
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

Do not upload your real API key to GitHub.

## Run the Application

Start the application using the project's main Python file.

Example:

```bash
python app.py
```

Then open the local URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## How It Works

1. User enters a comic idea or story prompt.
2. The application sends the request to the Gemini AI model.
3. Gemini generates the comic story and panel descriptions.
4. The image-generation component creates the panel images.
5. The generated comic panels are displayed on the web page.

## Security

API keys and other secret credentials should be stored in `.env` and excluded from GitHub using `.gitignore`.

## Future Improvements

* Download complete comics as PDF
* Add more comic styles
* Add character customization
* Add speech bubbles
* Add user accounts
* Improve image consistency between panels

## Author

ComicCraft AI Project
