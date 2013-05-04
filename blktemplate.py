from binascii import a2b_hex as __a2b_hex
import blkmaker as _blkmaker
from time import time as _time

try:
	__a2b_hex('aa')
	_a2b_hex = __a2b_hex
except TypeError:
	def _a2b_hex(a):
		return __a2b_hex(a.encode('ascii'))

def request(jcaps, lpid = None):
	params = {
		'capabilities': jcaps,
		'maxversion': _blkmaker.MAX_BLOCK_VERSION,
	}
	if lpid:
		params['longpollid'] = lpid
	req = {
		'id':0,
		'method': 'getblocktemplate',
		'params': [params],
	}
	return req

class _Transaction:
	def __init__(self, txnj):
		if 'data' not in txnj:
			raise ValueError("Missing or invalid type for transaction data")
		self.data = _a2b_hex(txnj['data'])

class _LPInfo:
	pass

class Template:
	def __init__(self):
		self.maxtime = 0xffffffff
		self.maxtimeoff = 0x7fff
		self.mintimeoff = -0x7fff
		self.maxnonce = 0xffffffff
		self.expires = 0x7fff
		self.cbtxn = None
		self.next_dataid = 0
		self.version = None
	
	def addcaps(self):
		# TODO: make this a lot more flexible for merging
		# For now, it's a simple "filled" vs "not filled"
		if self.version:
			return 0
		return ('coinbasetxn', 'workid', 'time/increment', 'coinbase/append')
	
	def get_longpoll(self):
		return self.lp
	
	def get_submitold(self):
		return self.submitold
	
	# Wrappers around blkmaker, for OO friendliness
	def get_data(self, usetime = None):
		return _blkmaker.get_data(self, usetime)
	def time_left(self, nowtime = None):
		return _blkmaker.time_left(self, nowtime)
	def work_left(self):
		return _blkmaker.work_left(self)
	def submit(self, data, dataid, nonce):
		return _blkmaker.submit(self, data, dataid, nonce)
	
	# JSON-specific stuff
	def request(self, lpid = None):
		return request(self.addcaps(), lpid)
	
	def add(self, json, time_rcvd = None):
		if time_rcvd is None: time_rcvd = _time()
		if self.version:
			return False;
		
		if 'result' in json:
			if json.get('error', None):
				raise ValueError('JSON result is error')
			json = json['result']
		
		self.diffbits = _a2b_hex(json['bits'])[::-1]
		self.curtime = json['curtime']
		self.height = json['height']
		self.prevblk = _a2b_hex(json['previousblockhash'])[::-1]
		self.sigoplimit = json['sigoplimit']
		self.sizelimit = json['sizelimit']
		self.version = json['version']
		
		self.cbvalue = json.get('coinbasevalue', None)
		self.workid = json.get('workid', None)
		
		self.expires = json.get('expires', self.expires)
		
		self.lp = _LPInfo()
		if 'longpollid' in json:
			self.lp.lpid = json['longpollid']
			self.lp.uri = json.get('longpolluri', None)
		self.submitold = json.get('submitold', True)
		
		self.txns = [_Transaction(t) for t in json['transactions']]
		
		if 'coinbasetxn' in json:
			self.cbtxn = _Transaction(json['coinbasetxn'])
		
		# TODO: coinbaseaux
		
		self.mutations = json.get('mutable', ())
		
		if (self.version > 2 or (self.version == 2 and not self.height)):
			if 'version/reduce' in self.mutations:
				self.version = 2 if self.height else 1
			elif 'version/force' not in self.mutations:
				raise ValueError("Unrecognized block version, and not allowed to reduce or force it")
		
		self._time_rcvd = time_rcvd;
		
		return True
