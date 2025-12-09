import firebase_admin
from firebase_admin import credentials, db
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import json

app = FastAPI(title="Kalcer Watch Dashboard")

# --- FIREBASE SETUP ---
cred = credentials.Certificate("serviceAccountKey.json")

# GANTI URL DI BAWAH INI SESUAI FIREBASE KAMU
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://kalcer-watch-default-rtdb.asia-southeast1.firebasedatabase.app'
})

templates = Jinja2Templates(directory="templates")

# --- KONFIGURASI DATABASE PATH ---
DB_CONTACTS = '/kontakDarurat'
DB_CURRENT  = '/sensorData/current'
DB_HISTORY  = '/sensorData/history'

# --- HALAMAN UTAMA ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    ref = db.reference(DB_CONTACTS)
    data = ref.get()
    contacts_list = []
    if data:
        for key, value in data.items():
            if isinstance(value, dict):
                value['id'] = key
                contacts_list.append(value)
    return templates.TemplateResponse("contacts.html", {"request": request, "contacts": contacts_list})

# --- API: REALTIME DATA ---
@app.get("/api/current-data")
async def get_current_data():
    """Mengambil data realtime (Single Object)"""
    ref = db.reference(DB_CURRENT)
    data = ref.get()
    
    # Fallback jika data kosong
    if not data:
        return {
            "heartRate": 0, "activity": "Menunggu Data...", 
            "anomaly": "Normal", "magnitude": 0, "hrStable": True,
            "isAnomalous": False, "temperature": 0
        }
    return data

# --- API: HISTORY DATA ---
@app.get("/api/history-data")
async def get_history_data():
    """Mengambil data history (Array of Objects)"""
    try:
        # Ambil 50 data terakhir dari Array history
        # Pada Firebase RTDB, array diakses dengan index integer (0, 1, 2...)
        # limit_to_last tetap bekerja berdasarkan index tersebut
        ref = db.reference(DB_HISTORY).order_by_key().limit_to_last(50)
        data = ref.get()
        
        chart_data = {"labels": [], "heartRate": [], "magnitude": []}
        
        # Helper function untuk ekstrak data dari 1 entry
        def process_entry(entry):
            if not entry: return
            
            # 1. Parsing Timestamp ("2025-12-09 22:54:10" -> "22:54")
            ts = entry.get('timestamp', '')
            time_label = ts.split(' ')[1][:5] if ' ' in ts else ts[-8:-3]
            
            chart_data["labels"].append(time_label)
            chart_data["heartRate"].append(entry.get('heartRate', 0))
            chart_data["magnitude"].append(entry.get('magnitude', 0))

        if data:
            # PENTING: Firebase mengembalikan List jika key-nya urut (0,1,2),
            # tapi mengembalikan Dict jika ada key yang bolong atau dimulai dari string.
            if isinstance(data, list):
                for entry in data:
                    process_entry(entry)
            elif isinstance(data, dict):
                for key, entry in data.items():
                    process_entry(entry)
        
        return chart_data
    except Exception as e:
        print(f"Error fetching history: {e}")
        return {"labels": [], "heartRate": [], "magnitude": []}

# --- LOGIC KONTAK ---
@app.post("/contacts/add")
async def add_contact(name: str = Form(...), phone: str = Form(...), chat_id: str = Form(...)):
    ref = db.reference(DB_CONTACTS)
    ref.push({
        'name': name,
        'phone': phone,
        'chat_id': chat_id 
    })
    return RedirectResponse(url="/contacts", status_code=303)

@app.post("/contacts/delete/{contact_id}")
async def delete_contact(contact_id: str):
    ref = db.reference(f'{DB_CONTACTS}/{contact_id}')
    ref.delete()
    return RedirectResponse(url="/contacts", status_code=303)

@app.get("/api/contacts")
async def get_contacts_json():
    ref = db.reference(DB_CONTACTS)
    data = ref.get()
    
    contacts_list = []
    if data:
        for key, value in data.items():
            if isinstance(value, dict):
                contacts_list.append({
                    "name": value.get('name', 'Tanpa Nama'),
                    "phone": value.get('phone', '-'),
                    "chat_id": value.get('chat_id', '') # Kirim Chat ID ke ESP32
                })
            
    return {"status": "ok", "data": contacts_list}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)