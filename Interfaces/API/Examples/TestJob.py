#!/usr/bin/env python

if __name__  == "__main__":
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    from ALDIRAC.Interfaces.API.Applications import Sewlab
    from ALDIRAC.Interfaces.API.Dirac import Dirac
    from ALDIRAC.Interfaces.API.UserJob import UserJob
    from DIRAC import gLogger, exit as dexit

    d = Dirac(True, "repo.rep")
    j = UserJob()
    j.setName("Test")
    j.setJobGroup("test")
    j.setCPUTime(1000)
    j.setOutputSandbox("*.log")

    s = Sewlab()
    sequence = ["""thickness = 22; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; label="extraction"; """, 
    """thickness = 43; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52;""",
    """thickness = 15; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 38; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; """,
    """thickness = 16; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 34; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; """,
    """thickness = 18; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 30; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; """,
    """thickness = 21; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 28; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; doping=0.15;""",
    """thickness = 25; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; doping=0.15;""",
    """thickness = 27; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; doping=0.15;""",
    """thickness = 32; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 27; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; """,
    """thickness = 36; material = AlInAs; x=0.48; mass=0.076;  gap=1.404; discont=-0.52; """,
    """thickness = 25; material = GaInAs; x=0.47; mass=0.0427; gap=0.790; discont=0.52; """ ]
    s.setSequence(sequence)
    s.setSelfTransportOptions(["--no-superself"])
    s.setSampleFile("sample-test.sample")
    s.setEfield(-10.)
    
    res = j.append(s)
    if not res["OK"]:
        gLogger.error(res["Message"])
        dexit(1)
    j.setLogLevel("VERBOSE")
    res = j.submit(d, mode="local")
    
    if not res['OK']:
        gLogger.error(res["Message"])
        dexit(1)
    else:
        gLogger.notice("JobIDs:", res['Value'])
        dexit()
