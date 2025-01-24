from typing import Optional


def quote(value: str) -> Optional[str]:
    """ encode spaces and comma """
    return None if not value else value.replace('\\', '\\\\').replace(' ','\\s').replace('|','\\v').replace(',','\\c').replace('\n','\\n')

def dequote(value: str) -> Optional[str]:
    """ decode spaces and comma """
    return None if not value else value.replace('\\n','\n').replace('\\c', ',').replace('\\v', '|').replace('\\s', ' ').replace('\\\\', '\\')

def str2bool(value: str) -> bool:
    return value.lower() in [ 'true', 'yes', 'visible', 'show', '1' ]
