import os
import cv2
import pytesseract
import numpy as np
import re
import math
import logging
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from sympy import symbols, Eq, solve, sympify
 
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
 
app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return gray

def extract_expression(image_path):
    processed_img = preprocess_image(image_path)
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789+-*/=√xX()'
    text = pytesseract.image_to_string(processed_img, config=custom_config)
    text = text.strip().replace('\n', '').replace(' ', '')
    logging.info(f'OCR Output: {text}')
    return text

def solve_expression(expression):
    
    try:
        expression = expression.replace('√', 'sqrt')
        expression = re.sub(r'([0-9]+)([xX])', r'\1*\2', expression)
        expression = expression.replace('X', 'x')
        
        if '=' in expression:
            left, right = expression.split('=')
            x = symbols('x')
            eq = Eq(sympify(left), sympify(right))
            solution = solve(eq, x)
            return {'expression': expression, 'result': f'x = {solution}'}
        else:
            result = eval(expression, {"math": math, "sqrt": math.sqrt})
            return {'expression': expression, 'result': result}
    except Exception as e:
        logging.error(f'Error solving expression: {e}')
        return {'expression': expression, 'error': str(e)}

def process_math_image(image_path):
    
    expression = extract_expression(image_path)
    solution = solve_expression(expression)
    solution['image_path'] = image_path.replace('static/', '')
    return solution

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            flash('Invalid file')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        result = process_math_image(filepath)
        return render_template('index.html', result=result)
    
    return render_template('index.html', result=None)

if __name__ == '__main__':
    app.run(debug=True)
