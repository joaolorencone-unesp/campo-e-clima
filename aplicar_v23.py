#!/usr/bin/env python3
"""Apply narrow, prevalidated v2.3 changes to a user-selected Git working tree.

No network, no commits, no pushes, no merges, no data changes.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BRANCH='feature/agro-ensembles-v23'

def repo_path_cli():
    parser=argparse.ArgumentParser(description='Instalar patch de ensembles do Campo e Clima em uma branch local')
    parser.add_argument('--repo', help='Pasta raiz do repositorio campo-e-clima (alternativa a janela de selecao)')
    opts=parser.parse_args()
    if opts.repo:return Path(opts.repo).expanduser().resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        ui=tk.Tk();ui.withdraw();ui.attributes('-topmost',True)
        result=filedialog.askdirectory(title='Selecione a pasta campo-e-clima do GitHub Desktop')
        ui.destroy()
        if result:return Path(result).resolve()
    except Exception as err:
        print('Nao foi possivel abrir o seletor de pastas:',err)
    return Path(input('Cole o caminho completo da pasta campo-e-clima: ').strip().strip('"')).resolve()

def main():
    repo=repo_path_cli()
    print('Pasta escolhida:',repo)
    if not (repo/'scripts/collect.py').is_file() or not (repo/'site/static/location.js').is_file():
        raise RuntimeError('Esta nao e a pasta raiz de campo-e-clima. Selecione a que contem as pastas scripts e site.')
    git_dir=repo/'.git'
    if not git_dir.is_dir():
        raise RuntimeError('Pasta .git nao encontrada. Abra a pasta conectada ao GitHub Desktop (nao o ZIP).')
    head=(git_dir/'HEAD').read_text(encoding='utf-8').strip()
    if head!=f'ref: refs/heads/{BRANCH}':
        current=head.replace('ref: refs/heads/','')
        raise RuntimeError('Branch atual: '+current+'\nNo GitHub Desktop, crie/selecione a branch '+BRANCH+' a partir da main ATUALIZADA antes de executar novamente.')
    exe=shutil.which('git')
    if exe:
        status=subprocess.run([exe,'-C',str(repo),'status','--porcelain'],capture_output=True,text=True)
        if status.returncode==0 and status.stdout.strip():
            raise RuntimeError('Existem alteracoes locais pendentes. Pare e verifique a aba Changes no GitHub Desktop. Nenhum arquivo foi alterado.')
    manifest=json.loads((HERE/'patches.json').read_text(encoding='utf-8'))
    staged={}
    for patch in manifest['patches']:
        relative=patch['path'];path=repo/relative
        current=path.read_text(encoding='utf-8')
        for idx,part in enumerate(patch['edits'],start=1):
            old,new=part['old'],part['new']
            if current.count(old)!=1:
                raise RuntimeError(f'O codigo {relative} mudou desde a preparacao (trecho {idx}). Nada foi alterado. Envie esta mensagem para revisarmos a versao.')
            current=current.replace(old,new,1)
        staged[relative]=current.encode('utf-8')
    additions=['scripts/agro_ensemble.py','site/static/agro_ensemble_v23.js',
               'tests/test_agro_ensemble_v23.py','tests/test_agro_ensemble_v23.cjs']
    for relative in additions:
        if (repo/relative).exists():
            raise RuntimeError(f'O arquivo {relative} ja existe. Nao vamos sobrescrever outra versao. Nenhum arquivo foi alterado.')
        staged[relative]=(HERE/'payload'/relative).read_bytes()
    for relative,payload in staged.items():
        if not payload or b'\x00' in payload:raise RuntimeError('Arquivo invalido: '+relative)
    backup=Path(tempfile.mkdtemp(prefix='campo_clima_v23_backup_'))
    applied=[]
    try:
        for relative in staged:
            src=repo/relative
            if src.exists():
                dest=backup/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dest)
        for relative,payload in staged.items():
            dest=repo/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_suffix(dest.suffix+'.v23tmp')
            tmp.write_bytes(payload)
            os.replace(tmp,dest)
            applied.append(relative)
    except Exception:
        for relative in reversed(applied):
            dest=repo/relative;previous=backup/relative
            if previous.exists():shutil.copy2(previous,dest)
            else:dest.unlink(missing_ok=True)
        raise
    print('\nSUCESSO: correcoes aplicadas SOMENTE NA PASTA LOCAL, na branch',BRANCH)
    print('Arquivos alterados/adicionados:')
    for relative in applied:print(' -',relative)
    print('Backup de seguranca:',backup)
    print('\nAGORA: abra o GitHub Desktop. Verifique Changes. Ainda NAO houve commit, push ou merge.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('\nNAO INSTALADO:',e)
        sys.exit(1)
