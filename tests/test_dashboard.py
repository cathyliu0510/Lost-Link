"""Meaningful state-machine checks through the UI bridge and real HTTP service."""
import json

from fastapi.testclient import TestClient

from dashboard.app import app


def test_live_dashboard_lifecycle_and_boundaries():
    with TestClient(app) as client:
        def action(name, **args):
            r = client.post('/demo/action', json={'action': name, **args})
            assert r.status_code == 200, r.text
            return r.json()

        state = action('search')
        assert state['mode'] == 'live'
        assert len(state['candidates']) == 3
        assert 'your_private_detail' not in json.dumps(state)
        found_id = state['candidates'][0]['report_id']
        state = action('claim', found_id=found_id, message='There is a cactus sticker near the cap.')
        cid = state['case']['case_id']
        assert state['case']['status'] == 'submitted'
        assert 'pickup_instructions' not in state['case']
        state = action('misuse')
        assert state['case']['status'] == 'submitted'
        assert state['events'][-1]['http']['status'] == 403
        state = action('repeat')
        assert state['case']['case_id'] == cid
        assert state['events'][-1]['detail']['duplicate_request'] is True
        review = action('review')['review']
        assert 'green cactus' in review['your_private_detail']
        assert 'cactus' in review['claim_message']
        action('clarify', note='What color is the sticker?')
        assert action('info', text='green')['case']['status'] == 'submitted'
        assert action('review')['review']['follow_up_info'] == ['green']
        state = action('approve', pickup='Hayden Library demo front desk')
        assert state['case']['pickup_instructions'] == 'Hayden Library demo front desk'
        state = action('returned')
        assert state['case']['status'] == 'returned'
        assert state['found_count'] == 5
        assert all(token not in json.dumps(state) for token in app.state.bridge.credentials.values())
        assert 'A green cactus sticker near the cap' not in json.dumps(state, ensure_ascii=False)
        action('reset')
        state = action('search', category='watch', color='black', description='black wristwatch')
        assert state['candidates'] == []
        assert client.post('/demo/action', json={'action':'claim','found_id':found_id,'message':'old'}).status_code == 400
        assert client.post('/demo/action', json={'action':'reset'}, headers={'Origin':'https://unrelated.example'}).status_code == 403
