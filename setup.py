from setuptools import setup, find_packages

setup(
    name='LLM_Excel',
    version='0.1.0',
    packages=find_packages(include=['modules', 'modules.*']), 
    py_modules=['main', 'app'],  
    install_requires=[
        'pandas>=1.3.0',
        'numpy>=1.20.0',
        'requests>=2.25.0',
        'python-dotenv>=0.19.0',
        'streamlit',
        'openai'
    ],
    entry_points={
        'console_scripts': [
            'app-main=main:main',  
        ],
    },
    author='Akhil Bongu',
    author_email='akhil.ssj2@gmail.com',
    description='Allows user to implement SQL queries with natural language on csv tables',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
