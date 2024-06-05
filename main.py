from time import time
from fastapi import FastAPI, __version__
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

html = f"""
<!DOCTYPE html>
<html>
    <head>
        <title>API for Multi Modal PDF</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
    </head>
    <body>
        <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
            <h1>API for Multi Modal PDF</h1>
            <ul>
                <li><a href="/generate-pdf">/generate-pdf</a></li>
                <li><a href="/docs">/docs</a></li>
                <li><a href="/redoc">/redoc</a></li>
                <li><a href="/ping">/ping</a></li>
            </ul>
        </div>
    </body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(html)

@app.get('/ping')
async def hello():
    return {'res': 'pong', 'version': __version__, "time": time()}

class Params(BaseModel):
    prompt: str

from openai import OpenAI
import os
import random
import uuid
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph,Frame
from reportlab.lib.styles import ParagraphStyle
import markdown as md

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post('/generate-pdf')
async def generate_pdf(params: Params):
    total_slides = random.randint(3, 5)
    content = []
    for i in range(total_slides):
        sub = "st" if i == 0 else "nd" if i == 1 else "rd" if i == 2 else "th"
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": "Assume you're the Wikipedia Bot. Give me only the " + str(i + 1) + sub + " slide content generated like human without any prompt text for '" + params.prompt + "'"
            }]
        )
        try:
            content.append(completion.choices[0].message.content)
        except Exception as e:
            print(e)

    images = []
    for i in range(total_slides):
        completion = client.images.generate(
            model="dall-e-3",
            prompt="Generate relevant images for the " + str(i + 1) + "/" + str(total_slides) + " slide content for '" + content[i] + "'",
            n=1
        )
        images.append(completion.data[0].url)

    filename = uuid.uuid4().hex + ".pdf"
    file_path = os.path.join("static", filename)
    c = canvas.Canvas(filename=file_path)
    c.setPageSize((1024, 768))
    c.setFont("Helvetica", 18)
    c.setLineWidth(2)
    headingStyle=ParagraphStyle(
        name="Heading",
        fontName="Helvetica",
        fontSize=22,
        leading=22,
        spaceAfter=12,
        alignment=4
    )
    styles=ParagraphStyle(
        name="Normal",
        fontName="Helvetica",
        fontSize=18,
        leading=18,
        spaceBefore=12,
        spaceAfter=12,
        alignment=4
    )
    for i in range(total_slides):
        text=[]
        rand = random.randint(1,100)
        content[i] = md.markdown(content[i])
        if rand % 2 == 0:
            c.drawImage(images[i], 0, 0, 512)
            frame = Frame(530, -10, 480, 768)
            text.append(Paragraph(content[i], style=headingStyle if i == 0 else styles))
            frame.addFromList(text, c)
        else:
            c.drawImage(images[i], 530, 0, 512)
            frame = Frame(10, -10, 512, 768)
            text.append(Paragraph(content[i], style=headingStyle if i == 0 else styles))
            frame.addFromList(text, c)
        c.showPage()
    c.save()

    return {
        'prompt': params.prompt,
        'file': file_path
    }