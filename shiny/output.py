from typing import Callable, Optional
from htmltools import *

def output_plot(id: str, width: str="100%", height: str="400px", inline: bool=False) -> tag:
  res = output_image(id=id, width=width, height=height, inline=inline)
  res.append(_class_="shiny-plot-output")
  return res

def output_image(id: str, width: str = "100%", height: str = "400px", inline: bool = False) -> tag:
  func = tags.span if inline else div
  style = None if inline else css(width=width, height=height)
  return func(id=id, _class_="shiny-image-output", style=style)

def output_text(id: str, inline: bool = False, container: Optional[Callable[[], tag_list]] = None) -> tag_list:
  if not container:
    container = tags.span if inline else tags.div

  return container(id = id, _class_ = "shiny-text-output")

def output_text_verbatim(id: str, placeholder: bool = False) -> tag:
  cls = "class-text-output" + (" noplaceholder" if not placeholder else "")
  return tags.pre(id = id, _class_ = cls)

def output_ui(id: str, inline: bool = False, container: Optional[Callable[[], tag_list]] = None, **kwargs) -> tag_list:
    if not container:
        container = tags.span if inline else tags.div
    return container(id=id, _class_="shiny-html-output", **kwargs)
