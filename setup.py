from setuptools import setup, find_packages


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
  name='query_smith',
  version='0.0.1',
  author='danny_two',
  author_email='primden4@gmail.com',
  description='This is the module for fast and convenient work with sql databases.',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/DanielPrim/QuerySmith',
  packages=find_packages(),
  install_requires=['asyncpg~=0.30.0'],
  classifiers=[
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent'
  ],
  keywords='orm sql pgsql postgresql',
  project_urls={
    'GitHub': 'https://github.com/DanielPrim/QuerySmith'
  },
  python_requires='>=3.9'
)
