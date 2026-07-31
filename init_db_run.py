import os
import sys
os.chdir('c:/Users/juanc/Downloads/ECOMMERCE_ENTERPRISE')
sys.path.insert(0, '.')
import scripts.init_db as init_db
init_db.main()
