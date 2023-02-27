from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declarative_base
from forms import CreatePostForm, RegisterForm, Login, CommentForm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from functools import wraps
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

#CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db: SQLAlchemy = SQLAlchemy(app)

# Configuring login_manager
login_manager = LoginManager()
login_manager.init_app(app)

# Relational Databases
Base = declarative_base()

# gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
class Users(UserMixin, db.Model, Base):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=False, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), unique=True, nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates='author')
    # *******Add parent relationship*******#
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship('Comment', back_populates='comment_author')


class BlogPost(db.Model, Base):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("Users", back_populates="posts")
    # ***************Parent Relationship*************#
    comments = relationship('Comment', backref="blog_post", cascade="all, delete-orphan")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model, Base):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # *******Add child relationship*******#
    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    comment_author = relationship("Users", back_populates='comments')

    blog_post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))


with app.app_context():
    db.create_all()


# flask decorator
def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(code=403)
        return func(*args, **kwargs)

    return wrapper


# User_Louder
@login_manager.user_loader
def load_user(use_id):
    return Users.query.get(int(use_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    wtf_form = RegisterForm()

    if request.method == "POST" and wtf_form.validate_on_submit():

        check_email = Users.query.filter_by(email=request.form['email']).first()
        if check_email:
            flash("you already signed up with that email", category='warning')
            return redirect(url_for("login"))

        else:
            new_user = Users()
            new_user.name = request.form['name']
            new_user.email = request.form['email']
            new_user.password = generate_password_hash(password=request.form['password'], method="pbkdf2:sha256",
                                                       salt_length=8)

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            return redirect(url_for('get_all_posts'))

    else:
        return render_template("register.html", form=wtf_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = Login()

    if request.method == "POST" and login_form.validate_on_submit():
        user = Users.query.filter_by(email=request.form['email']).first()
        if user:
            if check_password_hash(user.password, request.form['password']):
                login_user(user)
                flash(message="Login Successfully")
                return redirect(url_for('get_all_posts'))

            else:
                flash("Wrong Password credential please check and try again!!", category="warning")
                return render_template("login.html", form=login_form)

        else:
            flash("Wrong email credential please check and try again!!", category="warning")
            return render_template("login.html", form=login_form)

    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out! ")
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()

    requested_post = BlogPost.query.get(post_id)

    if request.method == "POST" and comment_form.validate_on_submit():
        if current_user.is_authenticated:
            add_comment = Comment(
                text=request.form['comment_section'],
                comment_author=current_user,
                blog_post_id=requested_post.id
            )
            db.session.add(add_comment)
            db.session.commit()
            return redirect(url_for('get_all_posts'))

        else:
            flash("you need to be Login to leave a comment!!", category="warning")
            return redirect(url_for('login'))

    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit() and request.method == "POST":
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
