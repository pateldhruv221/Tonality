#library imports
import os
from pathlib import Path
from random import randint
from flask import Flask, render_template, request, redirect, url_for
from backend.pitch_detection import analysis
from bs4 import BeautifulSoup
from markupsafe import Markup

#specifying the app
app = Flask(__name__)

# Define the folder where uploaded files will be stored
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define a global variable to store the selected option
selected_option = None

#list of final messages
final_messages_list = ["that sounded amazing", "you played that so well", "what a great recording"]

#analysis values
percent_score = None
errors = None
errors_html_element = None

#MAIN FLASK CODE

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/selection', methods=['GET', 'POST'])
def selection():
    global selected_option, percent_score, errors, errors_html_element

    musicxml_file = None
    audio_file = None

    if request.method == 'POST':

        #delete all the existing contents of upload
        [f.unlink() for f in Path("uploads").glob("*") if f.is_file()]

        selected_option = request.form.get('selected_option')

        if 'mxl_file' in request.files:
            mxl_file = request.files['mxl_file']
            if mxl_file.filename != '':
                mxl_filename = os.path.join(app.config['UPLOAD_FOLDER'], mxl_file.filename)
                musicxml_file = mxl_filename
                mxl_file.save(mxl_filename)
                
        if 'audio_video_file' in request.files:
            audio_video_file = request.files['audio_video_file']
            if audio_video_file.filename != '':
                audio_video_filename = os.path.join(app.config['UPLOAD_FOLDER'], audio_video_file.filename)
                audio_file = audio_video_filename
                audio_video_file.save(audio_video_filename)

        if mxl_file.filename != '' and audio_video_file.filename != '':
            #do calculations for the analysis
            percent_score, errors = analysis(selected_option, audio_file, musicxml_file)
            
            #post-process data
            percent_score=round(percent_score)
            
            num_notes = 0
            for bar in errors:
                num_notes += len(errors[bar])

            temp_dict = {}
            counter = 1
            for bar in errors:
                for note in errors[bar]:
                    temp_dict[f'note {counter}'] = errors[bar][note]
                    counter += 1
                errors[bar] = temp_dict
                #reset temp dict and counter
                counter = 1
                temp_dict = {}

            #removing perfect notes and bars from the errors dict
            keys_to_remove = []
            #removing perfect notes
            for bar in errors:
                for note in errors[bar]:
                    if len(errors[bar][note]) == 0:
                        keys_to_remove.append(note)
                for key in keys_to_remove:
                    errors[bar].pop(key)
                #reset the keys that have to be removed
                keys_to_remove = []
            #removing perfect bars
            for bar in errors:
                if len(errors[bar]) == 0:
                    keys_to_remove.append(bar)
            for key in keys_to_remove:
                errors.pop(key)

            #converting the errors dict to an html string
            errors_html_string = ""
            for bar in errors:
                errors_html_string += "<p>" + bar + "</p>\n"
                errors_html_string += "<ul>\n"
                for note in errors[bar]:
                    errors_html_string += "\t<li>" + note + ": " + str(
                        errors[bar][note]).replace("[", "").replace("]", "") + "</li>\n"
                errors_html_string += "</ul>\n"
            
            errors_html_string = "<div style=\"width:500px\">\n" + "<p>be careful of...</p>\n" + errors_html_string + "</div>"

            soup = BeautifulSoup(errors_html_string, 'html.parser')
            errors_html_element = soup.div
            errors_html_element = Markup(errors_html_element)

            return redirect(url_for('result'))

    return render_template('selection.html')

@app.route('/result')
def result():
    global selected_option, percent_score, errors
    selected_final_message = final_messages_list[randint(0, 2)]

    return render_template('result.html', selected_option=selected_option, selected_final_message=selected_final_message, percent_score=percent_score, errors_html_element=errors_html_element)

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8080, debug=True)
