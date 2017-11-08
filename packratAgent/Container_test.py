import pytest

from packratAgent.Container import Container


def test_load():
  Container( 'test_resources/docker-test_0.0.tar' )

  with pytest.raises( ValueError ):
    Container( 'test_resources/notexist' )

  with pytest.raises( ValueError ):
    Container( 'test_resources' )


def test_layers():
  c = Container( 'test_resources/docker-test_0.0.tar' )
  assert c.layers == [ 'c9677f6d879e9ff20694405684cc975f7b4fc71d6548ed76a38660da9b9b3cbb' ]
