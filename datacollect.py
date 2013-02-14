import resoncom
import hypackcom

def main():
    hc = hypackcom.HypackCom('UDP', 9888)
    hc.run_diag()

    resoncom.runsonar('192.168.0.101')

if __name__ == '__main__':
    main()