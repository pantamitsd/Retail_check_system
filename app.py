import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import threading
import pytz
import smtplib
from email.mime.text import MIMEText
import os

st.title("📦 Retail Order Management")

# -----------------------------
# DATE
# -----------------------------
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

today = datetime.now().strftime("%d-%m-%Y")
st.subheader(f"📅 Date: {today}")

date_time = now_ist.strftime("%d-%m-%Y %H:%M:%S")

# -----------------------------
# GOOGLE SHEET (STOCK)
# -----------------------------
stock_url = "https://docs.google.com/spreadsheets/d/1c_B12xm6U9k9InwSNmu7_dwFRhiXe-r2wRCgbZd2hLA/export?format=csv"

@st.cache_data(ttl=60)
def load_stock():
    df = pd.read_csv(stock_url)
    df.columns = df.columns.str.strip().str.upper()
    return df

df = load_stock()

# -----------------------------
# GOOGLE SHEET (PARTY)
# -----------------------------
@st.cache_data(ttl=60)
def load_parties():
    party_url = "https://docs.google.com/spreadsheets/d/1c_B12xm6U9k9InwSNmu7_dwFRhiXe-r2wRCgbZd2hLA/export?format=csv&gid=1688755592"
    party_df = pd.read_csv(party_url)
    party_df.columns = party_df.columns.str.strip().str.upper()
    return party_df

party_df = load_parties()

# -----------------------------
# PARTY EMAIL MAP
# -----------------------------
party_email_map = {}

if "EMAIL" in party_df.columns:
    party_email_map = dict(zip(party_df.iloc[:, 0], party_df["EMAIL"]))

# -----------------------------
# EMAIL FUNCTION
# -----------------------------
def send_email(to_email, subject, body):
    app_password = os.getenv("EMAIL_PASSWORD")
    sender_email = os.getenv("EMAIL_USER")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email Error:", e)

# -----------------------------
# USER NAME INPUT
# -----------------------------
user_name = st.text_input("👤 Your Name")

# -----------------------------
# PARTY INPUT
# -----------------------------
party_list = party_df.iloc[:, 0].dropna().unique().tolist()

party_option = st.selectbox("🏪 Select Party", ["-- Select --"] + party_list)
new_party = st.text_input("➕ Or Enter New Party")

if party_option != "-- Select --":
    party = party_option
elif new_party:
    party = new_party
else:
    party = None

# -----------------------------
# SESSION STATE
# -----------------------------
if "cart" not in st.session_state:
    st.session_state.cart = []

if "qty" not in st.session_state:
    st.session_state.qty = 1

if "last_sku" not in st.session_state:
    st.session_state.last_sku = None

# -----------------------------
# INPUT SECTION
# -----------------------------
st.subheader("➕ Add Item")

col1, col2 = st.columns(2)

with col1:
    sku_list = ["-- Select SKU --"] + df["SKU"].tolist()
    sku = st.selectbox("Select SKU", sku_list, key="sku")

    if st.session_state.last_sku != sku:
        st.session_state.qty = 1
        st.session_state.last_sku = sku

with col2:
    qty = st.number_input("Quantity", min_value=1, step=1, key="qty")

# -----------------------------
# ADD TO CART
# -----------------------------
if st.button("➕ Add to Cart"):
    found = False

    for item in st.session_state.cart:
        if item["SKU"] == sku:
            item["QTY"] += qty
            found = True
            break

    if not found:
        st.session_state.cart.append({
            "SKU": sku,
            "QTY": qty
        })

    st.success("Item Added ✅")

# -----------------------------
# CART DISPLAY
# -----------------------------
st.subheader("🧾 Your Order")

if st.session_state.cart:

    for i, item in enumerate(st.session_state.cart):

        st.markdown(f"""
        <div style="border:1px solid #ddd; padding:10px; border-radius:8px; margin-bottom:8px;">
            <div><b>SKU:</b> {item['SKU']}</div>
            <div><b>QTY:</b> {item['QTY']}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("❌ Remove", key=f"remove_{i}"):
            st.session_state.cart.pop(i)
            st.rerun()

    total_qty = sum([item["QTY"] for item in st.session_state.cart])
    st.info(f"Total Quantity: {total_qty}")

else:
    st.warning("Abhi koi item add nahi hua ❌")

# -----------------------------
# CLEAR CART
# -----------------------------
if st.button("🗑 Clear Cart"):
    st.session_state.cart = []
    st.rerun()

# -----------------------------
# SEND DATA TO SHEET
# -----------------------------
def send_data(payload):
    url = "https://script.google.com/macros/s/AKfycbxrezy8E1o4r98o_bVact_KQsfBLRxOFSz1PM3OQJjA3s6q7Ve6MtddUNYP56vzAese/exec"
    try:
        response = requests.post(url, json=payload, timeout=5)

        if response.status_code == 200:
            print("✅ Data sent successfully:", response.text)
        else:
            print("❌ Failed:", response.status_code, response.text)

    except Exception as e:
        print("🚨 Error:", e)

# -----------------------------
# SUBMIT ORDER
# -----------------------------
if st.button("✅ Submit Order"):

    if not user_name:
        st.warning("Apna naam daalo ❌")

    elif not party:
        st.warning("Party select ya enter karo ❌")

    elif not st.session_state.cart:
        st.warning("Cart khali hai ❌")

    else:
        payload = []

        for item in st.session_state.cart:
            payload.append({
                "date": date_time,
                "user": user_name,
                "party": party,
                "sku": str(item["SKU"]),
                "qty": int(item["QTY"])
            })

        # SEND TO GOOGLE SHEET
        threading.Thread(target=send_data, args=(payload,)).start()

        # -----------------------------
        # SEND EMAIL
        # -----------------------------
        customer_email = party_email_map.get(party)

        if customer_email:
            subject = "Order Received ✅"

            order_details = "\n".join(
                [f"{item['SKU']} - Qty: {item['QTY']}" for item in st.session_state.cart]
            )

            body = f"""
Hello {party},

Your order has been successfully placed.

User: {user_name}
Date: {date_time}

Order Details:
{order_details}

Status: Processing

Thanks,
Retail Team
"""

            threading.Thread(
                target=send_email,
                args=(customer_email, subject, body)
            ).start()

        st.session_state.cart = []

        st.success("Order Submitted 🚀")
        st.toast(f"Order placed by {user_name} ⚡")
