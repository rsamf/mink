import easyocr
import hydra
from omegaconf import DictConfig


@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg: DictConfig):
    print("Hello from mink!")
    reader = easyocr.Reader(
        cfg.ocr.lang
    )  # this needs to run only once to load the model into memory
    result = reader.readtext("download.jpeg")
    print(result)


if __name__ == "__main__":
    main()
