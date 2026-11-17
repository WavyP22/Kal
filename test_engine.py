import unittest
from datetime import datetime,timezone,timedelta
from engine import evidence_gate,scenario,enumerate_scenarios
NOW=datetime(2026,11,16,20,tzinfo=timezone.utc)
def row(game='A',league='NFL'):
    return dict(league=league,game_id=game,selection=game,source_kind='official',source_url='https://example.org/report',
        evidence_at=(NOW-timedelta(hours=1)).isoformat(),lineup='confirmed',injuries='accounted_for',
        suspensions='accounted_for',news='reviewed',news_at=(NOW-timedelta(hours=1)).isoformat(),
        model_status='backtested',model_reference='model-v1',model_at=(NOW-timedelta(hours=1)).isoformat(),
        p_low=.45,p_mid=.55,p_high=.65)
class Tests(unittest.TestCase):
    def test_claims_pass_but_not_verified(self):self.assertEqual(evidence_gate(row(),NOW),[])
    def test_stale_news_blocks(self):
        r=row();r['news_at']=(NOW-timedelta(hours=4)).isoformat();self.assertTrue(any('News' in x for x in evidence_gate(r,NOW)))
    def test_unknown_injury_blocks(self):
        r=row();r['injuries']='unknown';self.assertTrue(any('Injuries' in x for x in evidence_gate(r,NOW)))
    def test_duplicate_game_blocks(self):
        a=row();b=row();b['selection']='B';self.assertTrue(any('one game' in x for x in scenario([a,b],10,30,now=NOW)['issues']))
    def test_scenario_stays_ineligible(self):
        result=scenario([row('A'),row('B')],10,60,now=NOW);self.assertFalse(result['eligible']);self.assertAlmostEqual(result['low_joint'],.1025)
    def test_invalid_probability(self):
        r=row();r['p_low']=.8;self.assertIn('Invalid probability interval',evidence_gate(r,NOW))
    def test_no_future_timestamp(self):
        r=row();r['news_at']=(NOW+timedelta(hours=2)).isoformat();self.assertTrue(evidence_gate(r,NOW))
    def test_distinct_games_only(self):
        self.assertEqual(len(enumerate_scenarios([row('A'),row('A'),row('B')],2,10,30,0,.1,now=NOW)),2)
if __name__=='__main__':unittest.main()
