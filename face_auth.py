import boto3
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def verifier_visage(email, base64_image_live, image_reference_filename):
    
    chemin_image_ref = os.path.join('static', 'faces', image_reference_filename)
    
    if not os.path.exists(chemin_image_ref):
        return False, "Image de référence introuvable sur le serveur."

    # Utilisation de rekognition : IA provenant de AWS afin de comparer deux images (pratique ici donc pour le face auth)
    rekognition = boto3.client('rekognition', 
        region_name='eu-west-1', # L'IA de AWS fonctionne que sur cette région, askip c'est le hub de l'Europe (Irlande)
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    try:
        # Lire l'image de référence sur le disque (en bytes)
        with open(chemin_image_ref, 'rb') as ref_file:
            ref_bytes = ref_file.read()

        # Décoder l'image de la webcam (live)
        live_bytes = base64.b64decode(base64_image_live.split(',')[1])

        # Demander à l'IA d'AWS de comparer
        response = rekognition.compare_faces(
            SourceImage={'Bytes': ref_bytes},
            TargetImage={'Bytes': live_bytes},
            SimilarityThreshold=85.0 # Tolérance : 85% de ressemblance minimum
        )

        # Vérifier si on a un match
        if len(response['FaceMatches']) > 0:
            match = response['FaceMatches'][0]
            similarity = match['Similarity']
            print(f"Visage reconnu à {similarity:.2f}%")
            return True, "Authentification réussie"
        else:
            return False, "Le visage ne correspond pas."

    except Exception as e:
        print(f"Erreur Rekognition : {e}")
        return False, "Erreur lors de l'analyse du visage."