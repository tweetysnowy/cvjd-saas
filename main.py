import os
import stripe
from openai import OpenAI
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
PRICE_ID = os.getenv("PRICE_ID")
DOMAIN = os.getenv("DOMAIN")

stripe.api_key = STRIPE_SECRET_KEY
client = OpenAI(api_key=OPENAI_API_KEY)


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.post("/create-checkout-session")
def create_checkout_session():
    try:
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
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        return {"error": str(e)}


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/process")
async def process_files(
    request: Request,
    email: str = Form(...),
    cv: UploadFile = File(...),
    jd: UploadFile = File(...)
):
    try:
        cv_bytes = await cv.read()
        jd_bytes = await jd.read()
        
        cv_content = cv_bytes.decode("utf-8", errors="ignore")
        jd_content = jd_bytes.decode("utf-8", errors="ignore")


        prompt = f"""
        Optimize the following CV for the job description.
        Do not add false information.
        CV:
        {cv_content}
        JOB DESCRIPTION:
        {jd_content}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert resume optimizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        optimized_cv = response.choices[0].message.content


        message = Mail(
            from_email="info@curiocamp.com",
            to_emails=email,
            subject="Your Optimized CV",
            plain_text_content=optimized_cv,
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)

        return templates.TemplateResponse("success.html", {"request": request})

    except Exception as e:
        return {"error": str(e)}
