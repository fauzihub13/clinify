from flask import Flask, Response, render_template, request, redirect, url_for, url_for, jsonify
import cv2
import numpy as np
import os
import sys

# Menambahkan folder 'logic' ke dalam path Python jika diperlukan
sys.path.append(os.path.join(os.path.dirname(__file__), 'logic'))

# Mengimpor colors_dictionary dari folder logic
from colors_dictionary import COLORS

# Membuat instance Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Membuat variabel global untuk menyimpan gambar yang diunggah
uploaded_image = None
uploaded_image_path = None

# Membuat video capture untuk menangkap video dari webcam
cap = cv2.VideoCapture(0)

# COLOR PICKER FROM LIVE WEBCAM
# Fungsi untuk menentukan nama warna berdasarkan RGB
def get_color_name(rgb_color):
    min_distance = float('inf')
    closest_color_name = None
    for color_name, color_value in COLORS.items():
        distance = np.linalg.norm(np.array(rgb_color) - np.array(color_value))
        if distance < min_distance:
            min_distance = distance
            closest_color_name = color_name
    return closest_color_name

# Fungsi untuk menggambar pointer di tengah frame
def draw_hollow_pointer(frame):
    height, width, _ = frame.shape
    center_x, center_y = width // 2, height // 2
    pointer_size = 20  # Panjang garis pointer
    hollow_size = 5    # Ukuran lubang di tengah pointer

    # Membuat pointer tanda tambah dengan lubang di tengah
    color = (0, 0, 0)
    # Garis horizontal dengan lubang di tengah
    cv2.line(frame, (center_x - pointer_size, center_y), (center_x - hollow_size, center_y), color, 2)
    cv2.line(frame, (center_x + hollow_size, center_y), (center_x + pointer_size, center_y), color, 2)
    # Garis vertikal dengan lubang di tengah
    cv2.line(frame, (center_x, center_y - pointer_size), (center_x, center_y - hollow_size), color, 2)
    cv2.line(frame, (center_x, center_y + hollow_size), (center_x, center_y + pointer_size), color, 2)

# Fungsi untuk menggambar indikator warna berdasarkan RGB
def draw_color_indicator(frame, color):
    color = tuple(int(c) for c in color)
    height, width, _ = frame.shape
    indicator_width = 180
    indicator_height = 60
    center_x = width // 2
    top_left_x = center_x - indicator_width // 2
    cv2.rectangle(frame, (top_left_x, 10), (top_left_x + 50, 60), color, -1)
    color_name = get_color_name(color)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, color_name, (top_left_x + 60, 45), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.rectangle(frame, (top_left_x - 5, 5), (top_left_x + indicator_width + 5, indicator_height + 5), (255, 255, 255), 2)

# Fungsi untuk streaming video dari webcam
def generate_frames():
    while True:
        success, frame = cap.read()  # Membaca frame dari kamera
        if not success:
            break
        else:
            height, width, _ = frame.shape
            center_x, center_y = width // 2, height // 2

            # Mengambil warna di titik tepat tengah layar
            center_color = frame[center_y, center_x]

            # Gambar pointer dan color indicator
            draw_hollow_pointer(frame)
            draw_color_indicator(frame, center_color)

            # Encode frame ke format jpeg
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Menggunakan yield untuk mengirim frame secara streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Route untuk halaman webcam
@app.route('/webcam')
def webcam():
    return render_template('webcam.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# COLOR PICKER FROM UPLOADED IMAGE
# Route untuk upload gambar
@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    global uploaded_image, uploaded_image_path
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)

        if file:
            # Simpan gambar yang diunggah ke folder uploads
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Baca gambar menggunakan OpenCV
            uploaded_image = cv2.imread(filepath)
            uploaded_image_path = filepath

            # Render halaman dengan gambar yang diunggah
            return render_template('upload_image.html', image_path=url_for('static', filename='uploads/' + file.filename))

    return render_template('upload_image.html')

@app.route('/get_color_at', methods=['POST'])
def get_color_at():
    global uploaded_image
    if uploaded_image is None:
        return jsonify({'error': 'No image uploaded'}), 400

    try:
        # Mendapatkan koordinat x, y dari klik
        x = int(request.form['x'])
        y = int(request.form['y'])

        # Memastikan koordinat berada dalam batas gambar
        height, width, _ = uploaded_image.shape
        if x < 0 or x >= width or y < 0 or y >= height:
            return jsonify({'error': 'Coordinates out of bounds'}), 400

        # Mengambil warna RGB dari gambar pada koordinat (x, y)
        b, g, r = uploaded_image[y, x]
        b, g, r = int(b), int(g), int(r) 
        color_name = get_color_name([r, g, b])
        

        # Mengembalikan hasil warna dalam format JSON
        return jsonify({'color_name': color_name, 'rgb': {'r': r, 'g': g, 'b': b}})
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# Route untuk halaman utama
@app.route('/')
def home():
    return render_template('home.html')


# COLOR BLIND SIMULATION
@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

# Fungsi simulasi buta warna
def simulate_color_blindness(image, filter_type='clear'):
    if filter_type == 'deuteranopia':
        transform = np.array([[0.56667, 0.43333, 0],
                              [0.55833, 0.44167, 0],
                              [0, 0.24167, 0.75833]])
    elif filter_type == 'protanopia':
        transform = np.array([[0.367, 0.633, 0],
                              [0.125, 0.875, 0],
                              [0, 0.7, 0.3]])
    elif filter_type == 'tritanopia':
        transform = np.array([[0.95, 0.05, 0],
                              [0, 0.43333, 0.56667],
                              [0, 0.475, 0.525]])
    elif filter_type == 'achromatopsia':
        transform = np.array([[0.299, 0.587, 0.114],
                              [0.299, 0.587, 0.114],
                              [0.299, 0.587, 0.114]])
    elif filter_type == 'achromatomaly':
        transform = np.array([[0.618, 0.320, 0.062],
                              [0.163, 0.775, 0.062],
                              [0.163, 0.320, 0.516]])
    else:
        raise ValueError("Tipe buta warna tidak dikenal.")
    
    return cv2.transform(image, transform)

# Route untuk menangani frame yang dikirim dari frontend dan menerapkan filter
@app.route('/process', methods=['POST'])
def process():
    file = request.files['image'].read()
    nparr = np.frombuffer(file, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Mendapatkan filter dari request
    filter_type = request.form.get('filter', 'none')

    # Jika filter_type adalah 'none', tidak perlu menerapkan filter
    if filter_type == 'none':
        filtered_img = img  # Gunakan gambar asli tanpa filter
    else:
        # Menerapkan filter simulasi buta warna
        filtered_img = simulate_color_blindness(img, filter_type)

    # Encode kembali ke format JPEG dan kirim kembali ke frontend
    _, buffer = cv2.imencode('.jpg', filtered_img)
    return Response(buffer.tobytes(), mimetype='image/jpeg')


# Route untuk halaman webcam
@app.route('/camify')
def camify():
    return render_template('camify.html')


# Jalankan aplikasi Flask
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
