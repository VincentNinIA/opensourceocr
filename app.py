import streamlit as st
from mistralai import Mistral
import os
from dotenv import load_dotenv
import base64
from table_chunker import detect_tables, extract_markdown_tables, guess_table_type, stable_column_count
from pdf2image import convert_from_bytes
from PIL import Image
import io

load_dotenv()

st.set_page_config(
    page_title="OCR Mistral AI",
    page_icon="📄",
    layout="wide"
)

def encode_file_to_base64(file_bytes):
    """Convert file bytes to base64 string"""
    return base64.b64encode(file_bytes).decode('utf-8')

def pdf_to_png(pdf_bytes):
    """Convert PDF bytes to PNG image bytes (first page only)"""
    try:
        # Convertir le PDF en images (prend la première page)
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=300)

        if images:
            # Convertir l'image PIL en bytes PNG
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        else:
            raise ValueError("Aucune page trouvée dans le PDF")
    except Exception as e:
        raise Exception(f"Erreur lors de la conversion PDF: {str(e)}")

def ocr_with_mistral(file_base64, api_key):
    """Process image with Mistral AI OCR"""
    try:
        client = Mistral(api_key=api_key)

        # Utiliser l'endpoint OCR dédié de Mistral
        document = {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{file_base64}"
        }

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document=document,
            include_image_base64=True
        )

        # Extraire le texte markdown de toutes les pages
        all_text = []
        for page in ocr_response.pages:
            all_text.append(page.markdown)

        return "\n\n".join(all_text)
    except Exception as e:
        return f"Erreur: {str(e)}"

def main():
    st.title("📄 OCR avec Mistral AI")
    st.markdown("Uploadez une image ou un PDF pour extraire le texte")

    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        st.warning("⚠️ Clé API Mistral non configurée")
        api_key = st.text_input("Entrez votre clé API Mistral:", type="password")
        if not api_key:
            st.info("💡 Ajoutez votre clé API dans le fichier .env ou saisissez-la ci-dessus")
            st.stop()

    st.sidebar.header("Configuration")

    use_chunking = st.sidebar.checkbox(
        "Détection automatique des tableaux",
        value=False,
        help="Utilise PaddleOCR pour détecter et extraire les tableaux avant l'OCR. Améliore la précision pour les documents avec tableaux."
    )

    uploaded_files = st.file_uploader(
        "Choisissez une ou plusieurs images/PDFs",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Uploadez un ou plusieurs fichiers à analyser (les PDFs seront convertis en image)",
        accept_multiple_files=True
    )

    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} fichier(s) uploadé(s)")

        # Traiter chaque fichier
        for file_idx, uploaded_file in enumerate(uploaded_files, 1):
            st.markdown("---")
            st.subheader(f"📄 Fichier {file_idx}/{len(uploaded_files)}: {uploaded_file.name}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**📥 Aperçu**")

                # Lire le fichier
                file_bytes = uploaded_file.read()

                # Détecter si c'est un PDF
                is_pdf = uploaded_file.name.lower().endswith('.pdf')

                if is_pdf:
                    st.info("📄 PDF détecté - Conversion en PNG en cours...")
                    try:
                        # Convertir PDF en PNG
                        file_bytes = pdf_to_png(file_bytes)
                        st.success("✅ PDF converti en image")
                        st.image(file_bytes, caption="Page 1 du PDF (convertie)")
                    except Exception as e:
                        st.error(f"❌ Erreur de conversion: {str(e)}")
                        continue  # Passer au fichier suivant
                else:
                    st.image(file_bytes, caption="Image uploadée")

            with col2:
                st.markdown("**📝 Texte extrait**")

                # Lancer l'OCR automatiquement
                with st.spinner("Traitement OCR en cours..."):
                    # Mode avec chunking
                    if use_chunking:
                        with st.spinner("Détection des tableaux..."):
                            try:
                                table_regions = detect_tables(file_bytes, upscale_factor=1.5, padding=30)
                                st.info(f"🔍 {len(table_regions)} tableau(x) détecté(s)")
                            except Exception as e:
                                st.warning(f"Erreur lors de la détection: {str(e)}. Passage en mode standard.")
                                table_regions = []

                        if table_regions:
                            # Traiter chaque tableau séparément
                            all_results = []
                            for i, region in enumerate(table_regions):
                                with st.spinner(f"OCR du tableau {i+1}/{len(table_regions)}..."):
                                    result = ocr_with_mistral(region.crop_base64, api_key)

                                    # Analyser la qualité du résultat
                                    md_tables = extract_markdown_tables(result)
                                    best_table = max(md_tables, key=lambda x: len(x), default=[])
                                    table_type = guess_table_type(best_table)
                                    is_valid = stable_column_count(best_table)

                                    all_results.append({
                                        "index": i + 1,
                                        "text": result,
                                        "type": table_type,
                                        "valid": is_valid,
                                        "bbox": region.bbox
                                    })

                            # Combiner tous les résultats
                            extracted_text = "\n\n---\n\n".join([
                                f"## Tableau {r['index']} (Type: {r['type']}, Qualité: {'✅' if r['valid'] else '⚠️'})\n\n{r['text']}"
                                for r in all_results
                            ])
                        else:
                            # Fallback si aucun tableau détecté
                            file_base64 = encode_file_to_base64(file_bytes)
                            extracted_text = ocr_with_mistral(file_base64, api_key)
                    else:
                        # Mode standard sans chunking
                        file_base64 = encode_file_to_base64(file_bytes)
                        extracted_text = ocr_with_mistral(file_base64, api_key)

                    if extracted_text and not extracted_text.startswith("Erreur"):
                        st.success("✅ Extraction terminée")

                        # Tabs pour différents formats d'affichage
                        tab1, tab2 = st.tabs(["📋 Markdown (formaté)", "📝 Texte brut"])

                        with tab1:
                            st.markdown("### Aperçu formaté")
                            st.markdown(extracted_text)

                        with tab2:
                            st.text_area(
                                "Texte brut:",
                                extracted_text,
                                height=400,
                                help="Texte extrait en Markdown brut",
                                key=f"text_area_{file_idx}"
                            )

                        # Options de téléchargement
                        col_dl1, col_dl2 = st.columns(2)

                        with col_dl1:
                            st.download_button(
                                label="💾 Télécharger (Markdown)",
                                data=extracted_text,
                                file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_extrait.md",
                                mime="text/markdown",
                                use_container_width=True,
                                key=f"download_md_{file_idx}"
                            )

                        with col_dl2:
                            st.download_button(
                                label="📄 Télécharger (TXT)",
                                data=extracted_text,
                                file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_extrait.txt",
                                mime="text/plain",
                                use_container_width=True,
                                key=f"download_txt_{file_idx}"
                            )

                        st.info(f"📊 Nombre de caractères: {len(extracted_text)} | Pages: {extracted_text.count('##') + 1 if '##' in extracted_text else 1}")
                    else:
                        st.error(extracted_text)
    else:
        st.info("👆 Uploadez un ou plusieurs fichiers pour commencer")

        with st.expander("ℹ️ Comment utiliser cette application"):
            st.markdown("""
            1. **Configurez votre clé API** Mistral AI dans le fichier `.env`
            2. **Activez la détection automatique** des tableaux pour améliorer la précision (optionnel)
            3. **Uploadez** un ou plusieurs fichiers (PNG, JPG, JPEG ou PDF)
            4. **L'OCR se lance automatiquement** pour chaque fichier
            5. **Téléchargez** les textes extraits individuellement

            ### Fonctionnalités
            - **Upload multiple**: Uploadez plusieurs fichiers en une seule fois
            - **Support PDF**: Les PDFs sont automatiquement convertis en image (première page)
            - **OCR automatique**: Le traitement démarre dès l'upload, pour chaque fichier
            - **OCR standard**: Utilise l'endpoint OCR dédié de Mistral AI (mistral-ocr-latest)
            - **Détection automatique des tableaux**: Découpe et traite chaque tableau séparément (PaddleOCR + upscaling)
              - ⚠️ Nécessite plus de ressources (RAM)
              - Peut ne pas fonctionner sur le plan gratuit de Render
            """)

if __name__ == "__main__":
    main()
