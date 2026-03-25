import streamlit as st
import requests
import pdfplumber
import io
import datetime
import urllib3
import base64
from bs4 import BeautifulSoup
import urllib.parse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Jelovnik Karađorđe", page_icon="🍽️", layout="centered")

st.title("🍽️ Jelovnik - Učenički centar")
st.markdown("---")

API_KEY = "K81202078688957"

@st.cache_data(ttl=43200) 
def pronadji_najnoviji_link():
    adrese = [
        "https://www.ucenickicentar-bg.rs/sluzba-ishrane/",
        "https://www.ucenickicentar-bg.rs/"
    ]
    
    for adresa in adrese:
        try:
            odgovor = requests.get(adresa, verify=False, timeout=10)
            supa = BeautifulSoup(odgovor.text, 'html.parser')
            
            for a_tag in supa.find_all('a', href=True):
                link = a_tag['href']
                dekodiran_link = urllib.parse.unquote(link).lower() 
                
                if '.pdf' in dekodiran_link and ('jelovnik' in dekodiran_link or 'јеловник' in dekodiran_link):
                    return link
        except:
            continue
            
    return "https://www.ucenickicentar-bg.rs/wp-content/uploads/2026/03/%D0%88%D0%B5%D0%BB%D0%BE%D0%B2%D0%BD%D0%B8%D0%BA-%D0%BC%D0%B0%D1%80%D1%82-2026.-II-%D0%B4%D0%B5%D0%BE.pdf"

@st.cache_data(ttl=43200) 
def citaj_tabelu_munja(link, dan_u_mesecu):
    zaglavlje = {"User-Agent": "Mozilla/5.0"}
    odgovor = requests.get(link, headers=zaglavlje, verify=False, timeout=15)
    
    if odgovor.status_code != 200:
        return None, "Sajt doma nas blokira."
        
    ceo_tekst = ""
    ocr_url = "https://api.ocr.space/parse/image"
    
    try:
        with pdfplumber.open(io.BytesIO(odgovor.content)) as pdf:
            
            if dan_u_mesecu >= 16:
                indeks_stranice = (dan_u_mesecu - 16) // 4
            else:
                indeks_stranice = (dan_u_mesecu - 1) // 4
                
            if indeks_stranice >= len(pdf.pages):
                indeks_stranice = len(pdf.pages) - 1
                
            strana = pdf.pages[indeks_stranice]
            
            slika = strana.to_image(resolution=110).original
            slika = slika.convert('L') 
            
            img_byte_arr = io.BytesIO()
            slika.save(img_byte_arr, format='JPEG', quality=75) 
            base64_slika = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            payload = {
                'apikey': API_KEY,
                'language': 'rus', 
                'OCREngine': '2',   
                'isTable': 'true',  
                'base64Image': 'data:image/jpeg;base64,' + base64_slika
            }
            
            ocr_odg = requests.post(ocr_url, data=payload)
            rezultat = ocr_odg.json()
            
            if rezultat.get('IsErroredOnProcessing'):
                return None, f"GREŠKA na serveru."
            
            for deo in rezultat.get('ParsedResults', []):
                ceo_tekst += deo.get('ParsedText', '') + "\n"
                    
    except Exception as e:
         return None, f"Pukao je Python kod: {e}"
         
    return ceo_tekst, "OK"

# GLAVNI DEO PROGRAMA 
danas = datetime.date.today()
sutra = danas + datetime.timedelta(days=1)

formatiran_datum = danas.strftime("%d.%m.") 
dan_za_pretragu = danas.strftime("%d.%m.") 
sledeci_dan = sutra.strftime("%d.%m.") 
danasnji_dan_broj = danas.day 

najnoviji_url = pronadji_najnoviji_link()

st.subheader(f"📅 Meni za danas: {formatiran_datum}")

with st.spinner('Tražim šta imaš za obroke⚡'):
    tekst, status = citaj_tabelu_munja(najnoviji_url, danasnji_dan_broj)

if tekst:
    linije = tekst.split('\n')
    
    dorucak = []
    rucak = []
    vecera = []
    
    snimam = False
    
    for linija in linije:
        if dan_za_pretragu in linija:
            snimam = True
            continue 
            
        elif snimam and (sledeci_dan in linija or "Верзиа:" in linija):
            snimam = False
            break
            
        if snimam:
            if "ДОРУЧАК" in linija and "РУЧАК" in linija:
                continue
                
            kolone = linija.split('\t')
            
            if len(kolone) > 0 and kolone[0].strip() and kolone[0].strip() != "-":
                dorucak.append(kolone[0].strip())
                
            if len(kolone) > 1 and kolone[1].strip() and kolone[1].strip() != "-":
                rucak.append(kolone[1].strip())
                
            if len(kolone) > 2 and kolone[2].strip() and kolone[2].strip() != "-":
                vecera.append(kolone[2].strip())

    if dorucak or rucak or vecera:
        
        def ulepsaj_i_popravi(lista_hrane):
            popravljena_lista = []
            
            zamene = {
                "нь": "њ", "ль": "љ",
                "зогурт": "јогурт", "огурт": "јогурт", 
                "BOhe": "воће", "Bohe": "воће", "воне": "воће",
                "штапий": "штапић", "штапин": "штапић", 
                "туевином": "туњевином", 
                "цемом": "џемом", "унела": "јунећа", 
                "унени": "јунећи", "зунепа": "јунећа",
                "азвар": "ајвар", "а вар": "ајвар", 
                "ча)": "чај", "ча,": "чај", 
                "ослина": "ослића", "jaje": "јаје", 
                "пунена": "пуњена", "св.шницла": "свињска шницла", 
                "пилена": "пилећа", "кранска": "крањска"
            }
            
            for jelo in lista_hrane:
                lepo_jelo = jelo.replace("-", "🔹 ").strip()
                
                for lose, dobro in zamene.items():
                    lepo_jelo = lepo_jelo.replace(lose, dobro)
                    
                # --- NAŠ ČISTAČ ZA DUPLA SLOVA ---
                lepo_jelo = lepo_jelo.replace("јјогурт", "јогурт")
                lepo_jelo = lepo_jelo.replace("ччај", "чај")
                lepo_jelo = lepo_jelo.replace("  ", " ") # Briše duple razmake ako postoje
                
                if lepo_jelo:
                    popravljena_lista.append(lepo_jelo)
                    
            return popravljena_lista

        st.markdown("<br>", unsafe_allow_html=True) 
        
        tab_dorucak, tab_rucak, tab_vecera = st.tabs(["🍳 Doručak", "🍲 Ručak", "🍝 Večera"])
        
        with tab_dorucak:
            for jelo in ulepsaj_i_popravi(dorucak):
                st.markdown(f"**{jelo}**") 
                
        with tab_rucak:
            for jelo in ulepsaj_i_popravi(rucak):
                st.markdown(f"**{jelo}**")
                
        with tab_vecera:
            for jelo in ulepsaj_i_popravi(vecera):
                st.markdown(f"**{jelo}**")
                
    else:
        st.warning("⚠️ Ne mogu da pronađem obroke za današnji datum.")
            
else:
    st.error(f"❌ Nešto nije u redu: {status}")
    #streamlit run c:/Users/PC/OneDrive/Desktop/MojJelovnik/appks.py
