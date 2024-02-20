import json
import requests
from requests.exceptions import ConnectionError
import sqlite3
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox, colorchooser
from PIL import Image, ImageTk, UnidentifiedImageError
from io import BytesIO


def create_database():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    create_table_query = '''
    CREATE TABLE dogs (
        id INTEGER PRIMARY KEY,
        breed_name TEXT,
        avg_height REAL,
        avg_weight REAL,
        avg_life_span REAL,
        image_url TEXT
    );
    '''
    cursor.execute(create_table_query)
    return conn, cursor


def process_data(conn, cursor):
    try:
        url = 'https://api.thedogapi.com/v1/breeds'
        response = requests.get(url)

        if response.status_code == 200:
            try:
                data = response.json()

                for breed in data:
                    id = breed.get('id')
                    breed_name = breed.get('name')
                    height_range = breed.get('height').get('metric')
                    weight_range = breed.get('weight').get('metric')
                    life_span = breed.get('life_span')
                    image_id = breed.get('reference_image_id')
                    image_url = f'https://cdn2.thedogapi.com/images/{image_id}.jpg'

                    height_values = [float(value) for value in height_range.split(' - ')]
                    weight_values = [float(value) for value in weight_range.split(' - ')]
                    life_span_values = [int(value) for value in life_span.split() if value.isdigit()]

                    # Calculate the average values for each breed, as the values are given in ranges
                    # and we have to store real values in the database, and not ranges represented as string
                    avg_height = sum(height_values) / len(height_values)
                    avg_weight = sum(weight_values) / len(weight_values)
                    avg_life_span = sum(life_span_values) / len(life_span_values)

                    insert_query = 'INSERT INTO dogs VALUES (?, ?, ?, ?, ?, ?)'
                    cursor.execute(insert_query, (id, breed_name, avg_height, avg_weight, avg_life_span, image_url))

                conn.commit()
            except json.JSONDecodeError:
                print(f'An error occurred while decoding JSON')
        else:
            print(f'Unable to retrieve data.')
    except ConnectionError:
        print('Failed to establish a connection.')


def clear_database(cursor):
    delete_query = 'DELETE FROM dogs'
    cursor.execute(delete_query)
    cursor.connection.commit()


def recognize_column(number):
    if number == 1:
        column_name = 'avg_height'
        units = 'cm'
        name = 'Height'
    elif number == 2:
        column_name = 'avg_weight'
        units = 'kg'
        name = 'Weight'
    elif number == 3:
        column_name = 'avg_life_span'
        units = 'years'
        name = 'Life Span'
    return column_name, units, name


def calculate_average(cursor, column):
    cursor.execute('SELECT COUNT(*) FROM dogs')
    count = cursor.fetchone()[0]
    if count > 0:
        column_name, units, name = recognize_column(column)
        query = f'SELECT AVG({column_name}) FROM dogs'
        cursor.execute(query)
        result = round(cursor.fetchone()[0], 2)

        return name, str(result), units
    else:
        return 'Data not available!'


def create_bar_chart(cursor, column):
    try:
        column_name, units, name = recognize_column(column)
        cursor.execute(f'SELECT breed_name, {column_name} FROM dogs ORDER BY RANDOM() LIMIT 4')
        data = cursor.fetchall()

        x = [row[0] for row in data]
        y = [row[1] for row in data]

        fig = plt.figure(figsize=(11, 6))
        plt.bar(x, y, color='#a8a8a8')
        plt.xlabel('Breed Name', fontsize=20)
        plt.xticks(x)
        plt.ylabel(f'Average {name} in {units}', fontsize=20)
        plt.title(f'Average {name} of 4 Random Dogs', fontsize=24)

        fig.savefig('canvas.jpg')
    except TypeError:
        print('An error occurred while creating a bar chart.')


def get_pic_info(cursor):
    cursor.execute('SELECT * FROM dogs ORDER BY RANDOM() LIMIT 1')
    data = cursor.fetchone()

    if data:
        return data[1], data[5]
    else:
        return '', ''


def check_if_empty(cursor):
    cursor.execute('SELECT COUNT(*) FROM dogs')
    count = cursor.fetchone()[0]
    if count > 0:
        answer = messagebox.askyesno(title='Database', message='The database is not empty. Do you want to proceed and overwrite the existing data?')
        if answer is True:
            return 1
        else:
            return 0
    else:
        return 2


def process_gui(conn, cursor):
    window = tk.Tk()

    window.title('Doggies World')
    window.geometry('1500x740')

    # ---------------------MAIN_MENU---------------------
    main_menu = tk.Menu(master=window)
    main_menu.add_command(label='Fill Database', command=lambda: fill_database(conn, cursor))
    main_menu.add_command(label='Clear Database', command=lambda: clear_content(conn, cursor))
    window.config(menu=main_menu)

    # ---------------------COLOR_THEME---------------------
    def set_color_theme():
        color = colorchooser.askcolor(title='Select Color')
        if color[1] is not None:
            avg_button.config(bg=color[1])
            avg_menu.config(bg=color[1])
            avg_label.config(fg=color[1])
            pic_label.config(fg=color[1])
            chart_button.config(bg=color[1])
            pic_button.config(bg=color[1])
            chart_menu.config(bg=color[1])
            status_label.config(text='Color theme changed')

    color_menu = tk.Menu(master=main_menu, tearoff=False, font=('Arial', 16))
    color_menu.add_command(label='Choose Color', command=set_color_theme)
    main_menu.add_cascade(label='Color Theme', menu=color_menu)

    def fill_database(conn, cursor):
        result = check_if_empty(cursor)
        if result == 0:
            status_label.config(text='Database wasn\'t updated')
        if result == 1:
            clear_database(cursor)
            process_data(conn, cursor)
            conn.commit()
            status_label.config(text='Database was updated')
        if result == 2:
            process_data(conn, cursor)
            conn.commit()
            status_label.config(text='Database was filled in')

    def clear_content(conn, cursor):
        clear_database(cursor)
        conn.commit()
        status_label.config(text='Database Cleared')
        canvas_pic.delete('all')
        canvas_chart.delete('all')
        avg_label.config(text='Data is not available!')
        pic_label.config(text='Picture is not available!')

    def show_menu(event, menu):
        menu.post(event.x_root, event.y_root)

    # ---------------------BUTTON_1---------------------
    avg_button = tk.Button(master=window, text='Get Average Dog Value', font=('Arial', 22, 'bold'))
    avg_button.place(x=25, y=25)

    avg_menu = tk.Menu(master=window, tearoff=False, font=('Arial', 18))
    avg_menu.add_command(label='Height', command=lambda: select_avg_option(1))
    avg_menu.add_command(label='Weight', command=lambda: select_avg_option(2))
    avg_menu.add_command(label='Life Span', command=lambda: select_avg_option(3))

    def select_avg_option(option):
        result = calculate_average(cursor, option)
        avg_label.config(text=' '.join(result))
        if isinstance(result, tuple):
            status_label.config(text=f'Average {result[0]} was displayed')
        else:
            status_label.config(text='Average Value was not calculated because of empty database')

    # Associate the menu with the button
    avg_button.bind('<Button-1>', lambda event: show_menu(event, avg_menu))

    avg_label = tk.Label(master=window, font=('Arial', 18, 'italic'))
    avg_label.place(x=25, y=90)

    # ---------------------BUTTON_2---------------------
    canvas_chart = tk.Canvas(window)
    canvas_chart.place(x=425, y=100)

    def open_chart():
        try:
            chart = Image.open('canvas.jpg')
            width, height = chart.size

            canvas_chart.config(width=width, height=height)
            image_tk_1 = ImageTk.PhotoImage(chart)
            canvas_chart.create_image(0, 0, anchor=tk.NW, image=image_tk_1)
            canvas_chart.image = image_tk_1

            status_label.config(text='A Bar Chart was displayed')
        except FileNotFoundError:
            print('A bar chart file doesn\'t exist.')

    chart_button = tk.Button(master=window, text='Open Dog Chart', font=('Arial', 22, 'bold'))
    chart_button.place(x=425, y=25)

    chart_menu = tk.Menu(master=window, tearoff=False, font=('Arial', 18))
    chart_menu.add_command(label='Height chart', command=lambda: select_chart_option(1))
    chart_menu.add_command(label='Weight chart', command=lambda: select_chart_option(2))
    chart_menu.add_command(label='Life Span chart', command=lambda: select_chart_option(3))

    def select_chart_option(option):
        create_bar_chart(cursor, option)
        open_chart()

    chart_button.bind('<Button-1>', lambda event: show_menu(event, chart_menu))

# ---------------------BUTTON_3---------------------
    canvas_pic = tk.Canvas(master=window)
    canvas_pic.place(x=25, y=235)

    pic_label = tk.Label(master=window, font=('Arial', 18, 'italic'))
    pic_label.place(x=25, y=195)

    def open_pic():
        try:
            target_width = 370
            max_target_height = 465

            breed_name, image_url = get_pic_info(cursor)
            if not image_url == '':
                response = requests.get(image_url)
                dog_pic = Image.open(BytesIO(response.content))

                w, h = dog_pic.size
                aspect_ratio = w / h
                target_height = int(target_width / aspect_ratio)

                if target_height > max_target_height:
                    target_height = max_target_height
                    target_width = int(target_height * aspect_ratio)

                resized = dog_pic.resize((target_width, target_height))
                canvas_pic.config(width=target_width, height=target_height)
                image_tk_2 = ImageTk.PhotoImage(resized)
                canvas_pic.create_image(0, 0, anchor=tk.NW, image=image_tk_2)
                canvas_pic.image = image_tk_2

                pic_label.config(text=breed_name)
                status_label.config(text='A Dog Picture was displayed')
            else:
                pic_label.config(text='Picture is not available!')
                status_label.config(text='A picture of a dog couldn\'t be found because of empty database')

        except ConnectionError:
            print('A dog picture couldn\'t be downloaded due to connection issues.')
            status_label.config(text='A picture of a dog couldn\'t be found because of connection issues')

        except UnidentifiedImageError:
            print('Cannot identify image file.')

    pic_button = tk.Button(master=window, text='Open Dog Picture', font=('Arial', 22, 'bold'), command=open_pic)
    pic_button.place(x=25, y=130)

    # ---------------------STATUS_LABEL---------------------
    status_label = tk.Label(window, text='Ready', font=('Arial', 18, 'bold'), bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label.pack(side=tk.BOTTOM, fill=tk.X)
    # ---------------------CLOSE_BUTTON---------------------
    close_button = tk.Button(window, text='Close', font=('Arial', 22, 'bold'), bg='#F01C1C', command=window.quit)
    close_button.place(x=1400, y=25)

    window.mainloop()


def run():
    conn, cursor = create_database()
    process_gui(conn, cursor)
    conn.close()


if __name__ == "__main__":
    run()
