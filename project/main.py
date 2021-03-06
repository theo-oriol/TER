from . import db
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_login import login_required , current_user
from flask import Blueprint, render_template,request,current_app,redirect, url_for
from .backend import model_prediction
from PIL import Image
import base64
import numpy as np
import torch 
import pickle 
import io
from project import create_app
import os 
from werkzeug.utils import secure_filename
from .histo import loading_histo
from .detection import detection_image
from .active_learning import learning,move_img

main = Blueprint('main', __name__)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = create_app()

def save(dic):
    with open('project/script/save/historique', 'wb') as handle:
        pickle.dump(dic, handle, protocol=pickle.HIGHEST_PROTOCOL)

def load():
    with open('project/script/save/historique', 'rb') as handle:
        b = pickle.load(handle)
    return b 

device = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.load("project/script/save/model",map_location=torch.device(device))
detection_model = torch.load("project/script/save/detection_model",map_location=torch.device(device))


with open('project/script/save/simi', 'rb') as handle:
    all_simi = pickle.load(handle)
with open('project/script/save/path_simi', 'rb') as handle:
    all_path = pickle.load(handle)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/accueil')
@login_required
def accueil():
    return render_template('accueil.html')

@main.route('/Bibliotheque')
@login_required
def biblio():
    return render_template('Bibliotheque.html')
    
@main.route('/Historique')
@login_required
def histo():
    id = current_user.id
    id = str(id)
    print('id : ',id)
    if os.path.isfile('project/script/save/historique'):
        histo = load()
        if id in histo :
            image_histo , labels_histo = loading_histo(histo[id])
            result = []
            for el in image_histo :
                img = Image.open(el).convert('RGB')
                file_object = io.BytesIO()
                img.save(file_object, 'jpeg',quality=100)
                figdata_jgp = base64.b64encode(file_object.getvalue())
                result.append(figdata_jgp.decode('ascii'))
            return render_template('Historique.html',results=zip(result , labels_histo))
        else : print('None')
    else :
        print("None")

    return render_template('Historique.html')
    
@main.route('/Labellisation')
@login_required
def label():
    img = learning()
    if img == None :
        return render_template('Labellisation.html')

    file_object = io.BytesIO()
    img.save(file_object, 'jpeg',quality=100)
    figdata_jgp = base64.b64encode(file_object.getvalue())
    result = figdata_jgp.decode('ascii')

    return render_template('Labellisation.html', img = result)

@main.route('/Labellisation', methods=['GET', 'POST'])
@login_required
def labelised():
    classe = request.form.get('code')
    if classe != "" :     
        move_img(classe)
    return  redirect(url_for('main.label'))

@main.route('/Apropos')
@login_required
def ap():
    return render_template('apropos.html')

@main.route('/Analyse')
@login_required
def anal():
    return render_template('Analyse.html')

@main.route('/Analyse', methods=['GET', 'POST'])
@login_required
def analyse():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('Analyse.html')
        file = request.files['file']
        print(file)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = filename.replace('\\','/')
            file_url = os.path.join('project/images/', filename)
            file.save(file_url)



            origin = Image.open(file_url).convert('RGB')
            file_object = io.BytesIO()
            origin.save(file_object, 'jpeg',quality=100)
            figdata_jgp = base64.b64encode(file_object.getvalue())
            origine_saved = figdata_jgp.decode('ascii')

            path,label,element = model_prediction(file_url,device,model,all_simi,all_path)

            id = current_user.id
            id = str(id)
            if os.path.isfile('project/script/save/historique'):
                histo = load()
                if id in histo :
                    histo[id].insert(0,element[0]+"/"+filename)
                    if len(histo[id])>20 : histo[id].pop()
                    save(histo)
                else :
                    print(histo)
                    histo[id] = []
                    histo[id].insert(0,element[0]+"/"+filename)
                    save(histo)
            else:
                histo = {}
                histo[id] = []
                histo[id].insert(0,element[0]+"/"+filename)
                save(histo)


            result = []
            for el in path :
                img = Image.fromarray((el).astype(np.uint8))
                file_object = io.BytesIO()
                img.save(file_object, 'jpeg',quality=100)
                figdata_jgp = base64.b64encode(file_object.getvalue())
                result.append(figdata_jgp.decode('ascii'))
            return render_template('Analyse.html',image = origine_saved ,label = element[0], results=zip(result,label))
    return render_template('Analyse.html')

        
@main.route('/Detection', methods=['GET', 'POST'])
@login_required
def detec():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('Analyse.html')
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = filename.replace('\\','/')
            file_url = os.path.join('project/images/', filename)
            file.save(file_url)
            img = detection_image(file_url,detection_model)

            file_object = io.BytesIO()
            img.save(file_object, 'jpeg',quality=100)
            figdata_jgp = base64.b64encode(file_object.getvalue())
            result = figdata_jgp.decode('ascii')

            return render_template('Detected.html', image = result)

    return render_template('Detection.html')

    @main.route('/Detection')
    @login_required
    def detection():
        return render_template('Detection.html')