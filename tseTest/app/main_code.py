from data import db_session
from data.users import User
from forms.user import RegisterForm

from flask import Flask, url_for, request, render_template, redirect

from flask_wtf import FlaskForm
from werkzeug.exceptions import abort
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from app.data.tests import Tests, Questions, Answers
from app.data.users import Completed
from app.forms.user import LoginForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'my_secret_key'


# TODO: нормальные тесты, добавить типа дизайн и картинки, не работают разделы на создании теста, редактировании профиля и ошибках

def get_categories():
    db_sess = db_session.create_session()
    categs = db_sess.query(Tests.section).all()
    categories = []
    for category in categs:
        category = category[0]
        if category in categories:
            continue
        else:
            categories.append(category)
    return categories


def get_completed():
    db_sess = db_session.create_session()
    completed = db_sess.query(Completed).filter(Completed.user_id == current_user.id).all()
    return completed


def get_questions(test_id):
    db_sess = db_session.create_session()
    questions = db_sess.query(Questions).filter(Questions.test_id == test_id).all()
    return questions


def get_answers(test_id):
    db_sess = db_session.create_session()
    answers = db_sess.query(Answers).filter(Answers.test_id == test_id).all()
    return answers


def get_test(test_id):
    db_sess = db_session.create_session()
    test = db_sess.query(Tests).filter(Tests.id == test_id).first()
    return test


@app.route('/category<category>')
def category_tests(category):
    db_sess = db_session.create_session()
    tests = db_sess.query(Tests).filter(Tests.section == category).all()
    return render_template('categories.html', category=category, tests=tests, categories=get_categories())


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', categories=get_categories()), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', categories=get_categories()), 500


@app.route('/create_test')
def create_test():
    return render_template('create_test.html', categories=get_categories())


@app.route('/test_created')
def test_created():
    data = request.args
    db_sess = db_session.create_session()
    test = Tests(
        title=data.get('title'),
        section=data.get('section'),
        description=data.get('description')
    )
    db_sess.add(test)
    db_sess.flush()
    db_sess.refresh(test)
    test_id = test.id
    for i in range(1, 6):
        question = Questions(
            test_id=test_id,
            question=data.get(f'q{i}')
        )
        db_sess.add(question)
        db_sess.flush()
        db_sess.refresh(question)
        q_id = question.id
        right = data.get(f'r{i}')
        for j in range(1, 4):
            is_right = False
            if f'ans{i}.{j}' == right:
                is_right = True
            answer = Answers(
                question_id=q_id,
                test_id=test_id,
                answer=data.get(f'ans{i}.{j}'),
                is_right=is_right,
            )
            db_sess.add(answer)
    db_sess.commit()

    return render_template('test_created.html', categories=get_categories())


@app.route('/edit_profile')
def edit_profile():
    return render_template('edit_profile.html', categories=get_categories())


@app.route('/saved')
def saved():
    new_name = request.args.get('new_name')
    new_about = request.args.get('about')
    db_sess = db_session.create_session()
    db_sess.query(User).filter(User.id == current_user.id).update({"name": new_name})
    db_sess.query(User).filter(User.id == current_user.id).update({"about": new_about})
    db_sess.commit()
    return render_template('saved.html', categories=get_categories())


@app.route('/<int:test_id>/results')
def show_results(test_id):
    results = dict(request.args)
    right_count = list(results.values()).count('True')
    wrong_count = list(results.values()).count('False')

    test_title = get_test(test_id).title
    db_sess = db_session.create_session()
    completed = Completed(title=test_title, user_id=current_user.id, id=test_id)
    if not db_sess.query(Completed).filter(Completed.title == test_title).first():
        db_sess.add(completed)
        db_sess.commit()
    return render_template('results.html', right_count=right_count, wrong_count=wrong_count, test=test_id,
                           categories=get_categories())


@app.route('/<int:test_id>')
def test(test_id):
    questions = get_questions(test_id)
    test = get_test(test_id)
    answers = get_answers(test_id)
    return render_template('test.html', questions=questions, test=test, answers=answers, categories=get_categories())


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/main_page')
def main_page():
    db_sess = db_session.create_session()
    tests = db_sess.query(Tests).all()

    return render_template('main_page.html', tests=tests, categories=get_categories())


@app.route('/', methods=["POST", "GET"])
def landing_page():
    return render_template('start_page.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/profile')
def profile():
    return render_template('profile.html', completed=get_completed(), categories=get_categories())


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/main_page")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


if __name__ == '__main__':
    db_session.global_init("db/app_db.db")
    app.run(port=8080, host='127.0.0.1')
