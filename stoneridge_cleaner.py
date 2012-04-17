import shutil

import stoneridge

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_arguments()
    shutil.rmtree(stoneridge.workdir)
