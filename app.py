import streamlit as st
from mistralai import Mistral
import os
from dotenv import load_dotenv
import base64
from table_chunker import detect_tables, extract_markdown_tables, guess_table_type, stable_column_count

load_dotenv()

st.set_page_config(
    page_title="OCR Mistral AI",
    page_icon="📄",
    layout="wide"
)

def encode_file_to_base64(file_bytes):
    """Convert file bytes to base64 string"""
    return base64.b64encode(file_bytes).decode('utf-8')

def ocr_with_mistral(file_base64, file_type, api_key, use_pixtral=False):
    """Process document with Mistral AI OCR"""
    try:
        client = Mistral(api_key=api_key)

        if use_pixtral:
            # Utiliser Pixtral avec prompt personnalisé
            mime_type = "application/pdf" if file_type == "PDF" else "image/jpeg"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extrait tout le texte de ce document de manière exhaustive.
Pour les tableaux, au lieu de les reproduire en Markdown, décris leur contenu ligne par ligne de façon structurée et lisible.
Assure-toi d'extraire TOUT le contenu du document sans rien omettre."""
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:{mime_type};base64,{file_base64}"
                        }
                    ]
                }
            ]

            chat_response = client.chat.complete(
                model="pixtral-12b-2409",
                messages=messages
            )

            return chat_response.choices[0].message.content
        else:
            # Utiliser l'endpoint OCR dédié de Mistral
            if file_type == "PDF":
                document = {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{file_base64}"
                }
            else:
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
    st.markdown("Uploadez un document PDF ou une image pour extraire le texte")

    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        st.warning("⚠️ Clé API Mistral non configurée")
        api_key = st.text_input("Entrez votre clé API Mistral:", type="password")
        if not api_key:
            st.info("💡 Ajoutez votre clé API dans le fichier .env ou saisissez-la ci-dessus")
            st.stop()

    st.sidebar.header("Configuration")

    ocr_mode = st.sidebar.radio(
        "Moteur OCR:",
        ["OCR dédié", "Pixtral (avec prompt personnalisé)"],
        help="OCR dédié: rapide, format Markdown. Pixtral: plus flexible, meilleur contrôle sur les tableaux"
    )

    use_chunking = st.sidebar.checkbox(
        "Détection automatique des tableaux",
        value=False,
        help="Utilise PaddleOCR pour détecter et extraire les tableaux avant l'OCR. Améliore la précision pour les documents avec tableaux."
    )

    file_type = st.sidebar.radio(
        "Type de fichier:",
        ["PDF", "Image (PNG/JPG)"]
    )

    if file_type == "PDF":
        uploaded_file = st.file_uploader(
            "Choisissez un fichier PDF",
            type=["pdf"],
            help="Uploadez un document PDF à analyser"
        )
    else:
        uploaded_file = st.file_uploader(
            "Choisissez une image",
            type=["png", "jpg", "jpeg"],
            help="Uploadez une image à analyser"
        )

    if uploaded_file is not None:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📥 Document uploadé")

            # Lire le fichier
            file_bytes = uploaded_file.read()

            if file_type == "PDF":
                st.success(f"✅ PDF chargé: {uploaded_file.name}")
                st.info("Le PDF sera traité directement par l'OCR Mistral AI")
            else:
                st.image(file_bytes, caption="Image uploadée", width=None)

        with col2:
            st.subheader("📝 Texte extrait")

            if st.button("🚀 Lancer l'OCR", type="primary", use_container_width=True):
                with st.spinner("Traitement en cours..."):
                    use_pixtral = (ocr_mode == "Pixtral (avec prompt personnalisé)")

                    # Mode avec chunking pour les images uniquement
                    if use_chunking and file_type != "PDF":
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
                                    result = ocr_with_mistral(region.crop_base64, "Image (PNG/JPG)", api_key, use_pixtral)

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
                            extracted_text = ocr_with_mistral(file_base64, file_type, api_key, use_pixtral)
                    else:
                        # Mode standard sans chunking
                        file_base64 = encode_file_to_base64(file_bytes)
                        extracted_text = ocr_with_mistral(file_base64, file_type, api_key, use_pixtral)

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
                                help="Texte extrait en Markdown brut"
                            )

                        # Options de téléchargement
                        col_dl1, col_dl2 = st.columns(2)

                        with col_dl1:
                            st.download_button(
                                label="💾 Télécharger (Markdown)",
                                data=extracted_text,
                                file_name="texte_extrait.md",
                                mime="text/markdown",
                                use_container_width=True
                            )

                        with col_dl2:
                            st.download_button(
                                label="📄 Télécharger (TXT)",
                                data=extracted_text,
                                file_name="texte_extrait.txt",
                                mime="text/plain",
                                use_container_width=True
                            )

                        st.info(f"📊 Nombre de caractères: {len(extracted_text)} | Pages: {extracted_text.count('##') + 1 if '##' in extracted_text else 1}")
                    else:
                        st.error(extracted_text)
    else:
        st.info("👆 Uploadez un document pour commencer")

        with st.expander("ℹ️ Comment utiliser cette application"):
            st.markdown("""
            1. **Configurez votre clé API** Mistral AI dans le fichier `.env`
            2. **Choisissez le moteur OCR** (OCR dédié ou Pixtral)
            3. **Activez la détection automatique** des tableaux pour améliorer la précision (images uniquement)
            4. **Sélectionnez le type** de fichier (PDF ou Image)
            5. **Uploadez** votre document
            6. **Cliquez** sur "Lancer l'OCR"
            7. **Téléchargez** le texte extrait si nécessaire

            ### Modes disponibles
            - **OCR dédié**: Rapide, format Markdown structuré
            - **Pixtral**: Meilleur contrôle sur les tableaux via prompt personnalisé
            - **Détection automatique**: Découpe et traite chaque tableau séparément (PaddleOCR + upscaling)
            """)

if __name__ == "__main__":
    main()
