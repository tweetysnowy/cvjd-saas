import os
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = FastAPI()
templates = Jinja2Templates(directory="templates")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
PRICE_ID = os.getenv("PRICE_ID")
DOMAIN = os.getenv("DOMAIN")

client = OpenAI(api_key=OPENAI_API_KEY)
stripe.api_key = STRIPE_SECRET_KEY

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
 return templates.TemplateResponse("landing.html", {"request": request})

@app.post("/create-checkout-session")
async def create_checkout_session():
 session = stripe.checkout.Session.create(
 payment_method_types=["card"],
 line_items=[{
 "price": PRICE_ID,
 "quantity": 1,
 }],
 mode="payment",
 success_url=f"{DOMAIN}/upload",
 cancel_url=f"{DOMAIN}/",
 )
 return RedirectResponse(session.url)

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
 return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/process")
async def process(
 request: Request,
 cv: UploadFile,
 jd: UploadFile,
 email: str = Form(...)
):
 cv_text = (await cv.read()).decode()
 jd_text = (await jd.read()).decode()

 prompt = f"""
 Rewrite the CV below so it aligns strongly with the job description.
 Do not fabricate information.
 Keep all facts truthful.

 CV:
 {cv_text}

 Job Description:
 {jd_text}
 """

 response = client.chat.completions.create(
 model="gpt-4o-mini",
 messages=[{"role": "user", "content": prompt}]
 )

 optimized_cv = response.choices[0].message.content

 message = Mail(
 from_email="your_verified_email@example.com",
 to_emails=email,
 subject="Your Optimized CV",
 plain_text_content=optimized_cv
 )

 sg = SendGridAPIClient(SENDGRID_API_KEY)
 sg.send(message)

 return templates.TemplateResponse("success.html", {"request": request})