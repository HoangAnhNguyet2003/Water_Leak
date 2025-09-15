import { Component } from '@angular/core';
import { SidebarComponent } from "../sidebar/sidebar.component";
import { HeaderComponent } from '../header/headercomponent';
import { FooterComponent } from '../footer/footer.component';
import { RouterOutlet } from "@angular/router";

@Component({
  selector: 'app-main',
  standalone: true,
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
  imports: [SidebarComponent, RouterOutlet, FooterComponent, HeaderComponent]
})
export class MainComponent {

}
