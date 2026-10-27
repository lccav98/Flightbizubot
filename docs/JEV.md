# JEV no Flightbizubot

O JEV governa o trabalho dos agentes sobre este repositório. A operação do
bot não depende do JEV. `AGENTS.md` define o fluxo para Codex; `CLAUDE.md`
direciona o Claude Code às mesmas regras.

## Preparar o ambiente do agente

1. Instale/conecte seu servidor MCP JEV no host (Codex ou Claude Code),
   usando a instalação e as credenciais fornecidas pelo mantenedor do JEV.
   Não há servidor MCP distribuído por este repositório.
2. Configure credenciais no ambiente seguro do host, nunca no código,
   na configuração versionada ou no `.env` do bot.
3. Abra este checkout e confirme que o host disponibiliza as nove
   ferramentas abaixo. Quando necessário, recarregue a conexão MCP.
4. Inicie uma tarefa e confira respostas reais. A presença de `AGENTS.md`
   não instala o MCP e não garante execução automática das ferramentas.

| Ferramenta | Aplicação neste projeto |
|---|---|
| `jev_route_task` | Escolher estratégia com objetivo e evidências recentes. |
| `jev_guard_tool_call` | Avaliar alterações e ações consequentes antes de executá-las. |
| `jev_decide` | Comparar alternativas com critérios de capacidade e confiabilidade. |
| `jev_check_research` | Avaliar se a evidência sustenta uma afirmação. |
| `jev_memory_sync` | Retomar tarefas longas com estado local em `.jev/state.json`. |
| `jev_verify_tests` | Avaliar saída real e código de saída dos testes executados. |
| `jev_delegate_subagent` | Validar limites de responsabilidade antes da delegação real. |
| `jev_metrics` | Consultar métricas reais e evitar contagem duplicada de rotas. |
| `jev_review_completion` | Conferir os critérios de aceite antes de concluir. |

Use ferramentas conforme o tipo de tarefa; não force as nove chamadas em
uma edição trivial. Decisões JEV são orientação para o agente, não uma
barreira técnica universal que intercepta comandos do host. O roteador não
comprova troca do modelo principal da conversa. Indisponibilidade exige
relato explícito e execução manual do processo de revisão e validação.

O servidor pode resolver caminhos relativos no seu próprio diretório de
trabalho. Para memória e métricas, passe o caminho absoluto de `.jev` neste
checkout e confira o caminho retornado. Esses arquivos são locais e
ignorados pelo Git. Não inclua dados pessoais ou segredos em chamadas MCP.

## Validação reproduzível

Requisito: Python 3.11 ou superior. Não é necessário instalar as dependências
de produção para executar esta checagem:

```sh
python -W error scripts/validate.py
```

O comando pode ser chamado de qualquer diretório pelo caminho do script.
Ele compila em memória os arquivos Python da raiz, de `scripts/` e de
`tests/`, sem importar o bot, e roda os testes `unittest` offline. Falhas de
sintaxe, testes, ausência de testes ou warnings não tratados retornam código diferente de zero.
Nenhum arquivo `.pyc` é necessário. Os testes de banco carregam apenas
`database.py`, com configuração fictícia e SQLite temporário; não leem
`.env`, não acessam o banco real e não chamam Telegram ou serviços de tarifas.

A workflow **Validação offline** executa o mesmo comando em pull requests,
pushes para `main` e execução manual, em Python 3.11, 3.12 e 3.13, sem
credenciais JEV ou Telegram e com permissão `contents: read`.
Ela não chama o modelo JEV nem faz deployment. Para exigir essa checagem
antes do merge, configure a proteção de `main` no GitHub; adicionar uma
workflow não ativa proteção de branch automaticamente.

## Critérios para concluir uma alteração

- Escopo e decisões registrados; nenhuma mudança de runtime fora do pedido.
- Validação offline aprovada; mudanças lógicas têm testes pertinentes.
- Resultado JEV informado quando houver conexão; indisponibilidade descrita.
- Segredos e dados locais ausentes do diff.
- Limites declarados: sintaxe e testes SQLite não comprovam instalação das
  dependências, buscas reais, entrega Telegram, Docker ou operação 24/7.
- Testes externos só com autorização específica, ambiente isolado e dados
  de teste. Nunca use os assinantes reais como fixture.
