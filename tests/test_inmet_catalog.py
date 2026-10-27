from scripts.export_inmet_catalog import normalize


def test_inmet_catalog_normalization():
    sample=[{'VL_LATITUDE':'-23,2','VL_LONGITUDE':'-54,1','CD_ESTACAO':'A001','DC_NOME':'Teste','SG_ESTADO':'MS','CD_SITUACAO':'Operante'},
            {'VL_LATITUDE':'not a number','VL_LONGITUDE':'-54,1','CD_ESTACAO':'A002'},
            {'VL_LATITUDE':'-23,2','VL_LONGITUDE':'-54,1','CD_ESTACAO':'A001','DC_NOME':'Teste novo'}]
    x=normalize(sample)
    assert len(x)==1
    assert x[0]['latitude']==-23.2
    assert x[0]['name']=='Teste novo'


def test_inmet_catalog_rejects_bad_payload():
    import pytest
    with pytest.raises(ValueError):normalize({'error':'denied'})
