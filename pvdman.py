class PvdRecord:
  def __init__(self, pvdId, pvdInfo, netnsName):
    self.pvdId = pvdId
    self.pvdInfo = pvdInfo
    self.netnsName = netnsName


class PvdManager:
  pvds = {}
  __netnsIdGenerator = 0;

  
  def __getNetnsName():
    __netnsIdGenerator += 1;
    return 'mif-pvd-' + str(__netnsIdGenerator)

    
  def setPvd(ifaceName, pvdInfo):
    if (pvds[pvdInfo.pvdId] is None):
      pvd = PvdRecord(pvdInfo.pvdId, pvdInfo, __getNetnsName())
      pvds[pvd.pvdId] = pvd
      # TODO: create namespace and configure PvD parameters on a given interface
    else
      raise Exception('PvD duplicate error: PvD with given ID is already configured.')

      
  def removePvd(ifaceName, pvdId):
    # TBD