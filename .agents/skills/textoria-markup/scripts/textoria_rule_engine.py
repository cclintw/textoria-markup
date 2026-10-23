"""Validated literal, between, and regex matchers. No arbitrary Python execution."""
from __future__ import annotations
import re
from textoria_annotation import scope_matches


def validate_rule(rule):
    if not isinstance(rule,dict) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*',str(rule.get('id',''))):raise ValueError('Rule needs a stable ID.')
    allowed={'id','kind','before','after','include_boundaries','min_length','max_length','cross_paragraph','stop_chars','exclude','type','scope','pattern','group','flags','enabled','description'}
    if set(rule)-allowed:raise ValueError('Unsupported rule conditions: '+', '.join(sorted(set(rule)-allowed)))
    if 'enabled' in rule and not isinstance(rule['enabled'],bool):raise ValueError('Rule enabled must be boolean.')
    if not isinstance(rule.get('flags',''),str):raise ValueError('Regex flags must be a string.')
    if rule.get('kind') not in {'between','regex'}:raise ValueError('Rule kind must be between or regex.')
    if rule.get('cross_paragraph',False):raise ValueError('Cross-paragraph rules are not supported.')
    if rule['kind']=='between':
        if not all(isinstance(rule.get(k),str) and rule[k] for k in ['before','after']):raise ValueError('Between rules need literal before and after boundaries.')
        low,high=rule.get('min_length',1),rule.get('max_length',200)
        if type(low)!=int or type(high)!=int or not 1<=low<=high<=10000:raise ValueError('Invalid length limits.')
        if rule.get('include_boundaries',False):raise ValueError('This engine extracts only the text between boundaries.')
    else:
        pattern=rule.get('pattern','')
        if not isinstance(pattern,str) or not 0<len(pattern)<=2000:raise ValueError('Regex needs a pattern up to 2000 characters.')
        if set(rule.get('flags',''))-set('ims'):raise ValueError('Only i/m/s regex flags are supported.')
        # Keep the stdlib engine bounded: reject backreferences, lookarounds,
        # quantified groups, and repeated quantifiers; never execute file content.
        if re.search(r'\\[1-9]|\\g<|\(\?[=!<]|\)[*+{]|(?:[*+}]|\{\d+(?:,\d*)?\})[*+{]',pattern):raise ValueError('Regex exceeds the supported bounded subset; simplify or split the rule.')
        compiled=re.compile(pattern,sum({'i':re.I,'m':re.M,'s':re.S}[f] for f in set(rule.get('flags',''))))
        group=rule.get('group',0)
        if not isinstance(group,(str,int)) or isinstance(group,bool):raise ValueError('Invalid capture group.')
        if isinstance(group,int) and not 0<=group<=compiled.groups:raise ValueError('Missing capture group.')
        if isinstance(group,str) and group not in compiled.groupindex:raise ValueError('Missing named capture group.')
    if not isinstance(rule.get('stop_chars',[]),list) or any(not isinstance(c,str) or len(c)!=1 for c in rule.get('stop_chars',[])):raise ValueError('stop_chars must be individual characters.')
    scope=rule.get('scope',{})
    if not isinstance(scope,dict) or set(scope)-{'paragraph_ids','division_ids','document_ids'}:raise ValueError('Invalid rule scope.')
    for values in scope.values():
        if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v for v in values):raise ValueError('Scope needs ID lists.')
    if not isinstance(rule.get('exclude',[]),list) or any(not isinstance(v,str) for v in rule.get('exclude',[])):raise ValueError('exclude needs literal strings.')
    if not isinstance(rule.get('type'),str) or not rule['type']:raise ValueError('Rule needs a target type.')
    return rule


def matches(rule,text,paragraph):
    validate_rule(rule)
    if not scope_matches({'scope':rule.get('scope',{})},paragraph):return
    if rule['kind']=='between':
        cursor=0
        while True:
            left=text.find(rule['before'],cursor)
            if left<0:break
            start=left+len(rule['before']);right=text.find(rule['after'],start)
            if right>=0:
                end=right;hit=text[start:end]
                if rule.get('min_length',1)<=len(hit)<=rule.get('max_length',200) and not any(c in hit for c in rule.get('stop_chars',[])) and hit not in rule.get('exclude',[]):yield start,end
            cursor=left+1
    else:
        import subprocess,sys,json
        try:
            result=subprocess.run([sys.executable,str(__file__),'--regex-worker'],input=json.dumps({'rule':rule,'text':text},ensure_ascii=False),text=True,capture_output=True,timeout=2,check=True)
        except subprocess.TimeoutExpired:raise ValueError('Regex exceeded the two-second paragraph budget; simplify the rule.')
        except subprocess.CalledProcessError as exc:raise ValueError('Regex capture failed: '+exc.stderr[-400:])
        yield from (tuple(row) for row in json.loads(result.stdout))


def _regex_worker(rule,text):
    flags=sum({'i':re.I,'m':re.M,'s':re.S}[f] for f in set(rule.get('flags','')))
    result=[]
    for found in re.finditer(rule['pattern'],text,flags):
        start,end=found.span(rule.get('group',0))
        if start<0 or end<=start:continue
        hit=text[start:end]
        if len(hit)>10000:raise ValueError('Regex capture exceeds length limit.')
        if hit not in rule.get('exclude',[]) and not any(c in hit for c in rule.get('stop_chars',[])):result.append([start,end])
        if len(result)>10000:raise ValueError('Too many regex matches in one paragraph.')
    return result

if __name__=='__main__':
    import json,sys
    payload=json.load(sys.stdin);print(json.dumps(_regex_worker(payload['rule'],payload['text'])))
