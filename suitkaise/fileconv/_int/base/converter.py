from pieces import __all__


class Converter(ABC):

    def __ascii__(self, piece: AsciiPiece) -> str:

    def __unicode__(self, piece: UnicodePiece) -> str:

    def __link__(self, piece: LinkPiece) -> str:

    def __url_image__(self, piece: URLImagePiece) -> str:

    def __local_image__(self, piece: LocalImagePiece) -> str:




