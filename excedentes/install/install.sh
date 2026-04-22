cp excedentes.service /etc/systemd/system/excedentes.service
sudo systemctl daemon-reload
sudo systemctl enable excedentes.service
sudo systemctl start excedentes.service

systemctl status excedentes.service
journalctl -u excedentes -f
