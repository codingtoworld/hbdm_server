# 火币合约API交易 服务器端
> 本服务器端需配合客户端一起使用

## 文件结构解析
```markdown
│  config.py
│  README.md
│  requirements.txt
│  trade_hbdm.py
├─api
│  │  HuobiDMService.py
│  │  HuobiDMUtil.py
│  └─  __init__.py

├─cert
│      fullchain.cer
│      server.key
│
└─utils
    │  daemon.py
    │  googleCode.py
    │  utils.py
    └─  __init__.py
```

## 重要文件说明

* config.py 服务器端配置文件，主要配置用户部分USERS_CONFIG = {}
* requirements.txt 运行本项目需要的Python包
* trade_hbdm.py 服务主文件
* cert/* https和wss所需要的证书文件
* utils/daemon.py Linux后台运行进程框架文件
* utils/googleCode.py 客户端登录时的Google Auth code 文件
* utils/utils.py 通用函数

## 系统部署步骤
1、准备一个Linux 服务器（推荐使用Linux，Windows系统也可以支持，但稳定性稍差）
> Linux 服务器连接火币服务器（api.hbdm.com）要求速度必须快,延时小；
> 操作系统可以是CentOS, Red Hat, Ubuntu, Debian, 或是Unix（FreeBSD）只要可以运行Python的系统都行；
> 服务器可以购买日本，美国，新加坡等国外的VPS

2、安装Python环境
> 本项目对Python版本要求非常低，只要是Python2.7.5以上的版本都可以；
> 大部分操作系统自带Python环境，推荐直接使用CentOS7.X版本的操作系统
> 如果需要自行安装Python环境，[请参考视频](https://www.youtube.com/watch?v=M2uoep0i8AQ)

3、安装必要的Python扩展包
```markdown
pip install -r requirements.txt
```

4、下载本项目到服务器/home/wwwroot/hbdm.com
> 这个目录可以自己定义，只是需要在代码（trade_hbdm.py）中进行对应即可

5、其他必要步骤
```markdown
1、 域名，需要一个域名，解析到本服务器IP地址
2、只要与域名匹配的证书文件cert/*，可以使用letsencrypt生成免费证书，每3个月更新一下
3、配置congfig.py中的USERS_CONFIG = {}部分，主要是Google Auth code密钥，火币API Key和密钥
4、服务器对外的443端口（https）需要是空闲未被占用，且服务器防火墙开放此端口
```

6、启动本项目
```markdown
cd /home/wwwroot/hbdm.com
python trade_hbdm.py start

执行start，restart，stop分别代表启动，重启，关闭

```

7、使用客户端程序连接运行，Enjoy Your Tradding...

## 附加说明
> 自动止损，止盈部分涉及到每个人的策略不同，在服务器端删除了这部分代码，你可以根据自己特性添加。

## 捐赠和定制化服务

### How to donate?
![image](https://resource.bnbstatic.com/images/20180806/1533543864307_s.png) BitCoin: 1K5apYN4k3UNdymo3qSfRWAehgri3skczQ

![image](https://resource.bnbstatic.com/images/20180806/1533543997535_s.png) ETH: 0x1eee99743dfddf6a4b6402047c1946ce9943c965

![image](https://resource.bnbstatic.com/images/20180810/1533888627851_s.png) USDT: 1KYvKoWDfoY8Xm2VNKoRWC9HgxtV3MbJRp

### 定制服务
请联系 coddingtoworld@gmail.com 洽谈